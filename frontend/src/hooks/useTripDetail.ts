import { useEffect, useMemo, useState } from "react";

import { createExpense, deleteExpense, updateExpense } from "../api/expenses";
import { createParticipant, deleteParticipant } from "../api/participants";
import { getSettlements } from "../api/settlements";
import { getTrip } from "../api/trips";
import type { Expense, ExpenseCreate, ExpenseUpdate, Settlement, Trip } from "../types";
import { type CurrencyCode, currencies, normalizeCurrency } from "../utils/currency";
import { getExpenseType } from "../utils/expenses";

export function useTripDetail(tripId: string | undefined) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadTrip(showLoading = true): Promise<Trip | null> {
    if (!tripId) return null;
    if (showLoading) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const [nextTrip, settlementSummary] = await Promise.all([
        getTrip(tripId),
        getSettlements(tripId),
      ]);
      setTrip(nextTrip);
      setSettlements(settlementSummary.settlements);
      return nextTrip;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load trip");
      return null;
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadTrip();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId]);

  const participantNames = useMemo(() => {
    return new Map(
      trip?.participants.map((participant) => [participant.id, participant.name]) ?? [],
    );
  }, [trip]);

  const spendingByCurrency = useMemo(
    () => sumByCurrency(trip?.expenses ?? [], () => true),
    [trip],
  );

  const sharedSpendingByCurrency = useMemo(
    () => sumByCurrency(trip?.expenses ?? [], (expense) => getExpenseType(expense) === "shared"),
    [trip],
  );

  const personalSpendingByCurrency = useMemo(
    () => sumByCurrency(trip?.expenses ?? [], (expense) => getExpenseType(expense) === "personal"),
    [trip],
  );

  const categorySummary = useMemo(() => {
    const totals = new Map<
      string,
      {
        category: Expense["category"];
        currency: CurrencyCode;
        shared: number;
        personal: number;
      }
    >();

    for (const expense of trip?.expenses ?? []) {
      const expenseCurrency = normalizeCurrency(expense.currency);
      const key = `${expense.category}:${expenseCurrency}`;
      const current = totals.get(key) ?? {
        category: expense.category,
        currency: expenseCurrency,
        shared: 0,
        personal: 0,
      };

      if (getExpenseType(expense) === "personal") {
        current.personal += expense.amount;
      } else {
        current.shared += expense.amount;
      }

      totals.set(key, current);
    }

    return Array.from(totals.values())
      .map((item) => ({
        ...item,
        total: item.shared + item.personal,
      }))
      .filter((item) => item.total > 0)
      .sort((first, second) => second.total - first.total);
  }, [trip]);

  const participantSpendingSummary = useMemo(() => {
    return (trip?.participants ?? []).map((participant) => {
      const paid = new Map<CurrencyCode, number>();
      const sharedPaid = new Map<CurrencyCode, number>();
      const sharedResponsibility = new Map<CurrencyCode, number>();
      const personal = new Map<CurrencyCode, number>();

      for (const expense of trip?.expenses ?? []) {
        const expenseCurrency = normalizeCurrency(expense.currency);
        if (expense.paid_by === participant.id) {
          paid.set(expenseCurrency, (paid.get(expenseCurrency) ?? 0) + expense.amount);
        }

        if (getExpenseType(expense) === "personal") {
          if (expense.paid_by === participant.id) {
            personal.set(
              expenseCurrency,
              (personal.get(expenseCurrency) ?? 0) + expense.amount,
            );
          }
          continue;
        }

        if (expense.paid_by === participant.id) {
          sharedPaid.set(
            expenseCurrency,
            (sharedPaid.get(expenseCurrency) ?? 0) + expense.amount,
          );
        }

        if (expense.split_among.includes(participant.id)) {
          const amountCents = Math.round(expense.amount * 100);
          const sortedIds = [...expense.split_among].sort();
          const baseCents = Math.floor(amountCents / sortedIds.length);
          const remainder = amountCents % sortedIds.length;
          const participantIndex = sortedIds.indexOf(participant.id);
          const shareCents = baseCents + (participantIndex < remainder ? 1 : 0);
          sharedResponsibility.set(
            expenseCurrency,
            (sharedResponsibility.get(expenseCurrency) ?? 0) + shareCents / 100,
          );
        }
      }

      const currencyCodes = new Set<CurrencyCode>([
        ...sharedPaid.keys(),
        ...sharedResponsibility.keys(),
      ]);
      const netBalances = Array.from(currencyCodes).map((code) => ({
        currency: code,
        amount: (sharedPaid.get(code) ?? 0) - (sharedResponsibility.get(code) ?? 0),
      }));

      const toMoneyList = (source: Map<CurrencyCode, number>) =>
        currencies
          .map((item) => ({
            currency: item.code,
            amount: source.get(item.code) ?? 0,
          }))
          .filter((item) => item.amount > 0);

      return {
        participant,
        paid: toMoneyList(paid),
        sharedResponsibility: toMoneyList(sharedResponsibility),
        personal: toMoneyList(personal),
        netBalances,
      };
    });
  }, [trip]);

  const tripCurrencyCodes = useMemo(() => {
    return Array.from(
      new Set((trip?.expenses ?? []).map((expense) => normalizeCurrency(expense.currency))),
    );
  }, [trip]);

  const settlementCurrency =
    tripCurrencyCodes.length <= 1 ? tripCurrencyCodes[0] ?? "USD" : null;

  async function addParticipant(name: string): Promise<void> {
    if (!tripId || !name.trim()) return;

    setIsSaving(true);
    setError(null);
    try {
      await createParticipant(tripId, { name: name.trim() });
      await loadTrip();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add participant");
    } finally {
      setIsSaving(false);
    }
  }

  async function removeParticipant(participantId: string): Promise<void> {
    if (!tripId) return;

    setIsSaving(true);
    setError(null);
    try {
      await deleteParticipant(tripId, participantId);
      await loadTrip();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove participant");
    } finally {
      setIsSaving(false);
    }
  }

  async function saveExpense(
    payload: ExpenseCreate,
    editingExpenseId: string | null,
  ): Promise<Trip | null> {
    if (!tripId) return null;

    setIsSaving(true);
    setError(null);
    try {
      if (editingExpenseId) {
        await updateExpense(tripId, editingExpenseId, payload as ExpenseUpdate);
      } else {
        await createExpense(tripId, payload);
      }
      return await loadTrip(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save expense");
      return null;
    } finally {
      setIsSaving(false);
    }
  }

  async function removeExpense(expense: Expense): Promise<boolean> {
    if (!tripId) return false;

    setIsSaving(true);
    setError(null);
    try {
      await deleteExpense(tripId, expense.id);
      await loadTrip();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete expense");
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  return {
    trip,
    settlements,
    isLoading,
    isSaving,
    error,
    setError,
    participantNames,
    spendingByCurrency,
    sharedSpendingByCurrency,
    personalSpendingByCurrency,
    categorySummary,
    participantSpendingSummary,
    settlementCurrency,
    addParticipant,
    removeParticipant,
    saveExpense,
    removeExpense,
  };
}

function sumByCurrency(
  expenses: Expense[],
  predicate: (expense: Expense) => boolean,
): Array<{ currency: CurrencyCode; amount: number }> {
  const totals = new Map<CurrencyCode, number>();

  for (const expense of expenses) {
    if (!predicate(expense)) continue;
    const expenseCurrency = normalizeCurrency(expense.currency);
    totals.set(expenseCurrency, (totals.get(expenseCurrency) ?? 0) + expense.amount);
  }

  return currencies
    .map((item) => ({
      currency: item.code,
      amount: totals.get(item.code) ?? 0,
    }))
    .filter((item) => item.amount > 0);
}
