import { useEffect, useMemo, useState } from "react";

import { getDashboard } from "../api/dashboard";
import { createExpense, deleteExpense, updateExpense } from "../api/expenses";
import {
  createParticipant,
  deleteParticipant,
  inviteParticipant,
} from "../api/participants";
import { getSettlements } from "../api/settlements";
import { deleteTrip, getTrip, updateTrip } from "../api/trips";
import type {
  DashboardSummary,
  Expense,
  ExpenseCreate,
  ExpenseUpdate,
  Settlement,
  Trip,
  TripUpdate,
} from "../types";
import { type CurrencyCode, currencies, normalizeCurrency } from "../utils/currency";
import { getExpenseType } from "../utils/expenses";

export function useTripDetail(tripId: string | undefined) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
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
      const [nextTrip, settlementSummary, dashboardSummary] = await Promise.all([
        getTrip(tripId),
        getSettlements(tripId),
        getDashboard(tripId),
      ]);
      setTrip(nextTrip);
      setSettlements(settlementSummary.settlements);
      setDashboard(dashboardSummary);
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

  const tripCurrencyCodes = useMemo(() => {
    return Array.from(
      new Set((trip?.expenses ?? []).map((expense) => normalizeCurrency(expense.currency))),
    );
  }, [trip]);

  const settlementCurrency =
    tripCurrencyCodes.length <= 1 ? tripCurrencyCodes[0] ?? "USD" : null;

  // Paid and personal totals are trivial per-currency sums with no
  // splitting logic, so they're safe to compute here. Shared
  // responsibility and net balance come from the backend's /dashboard
  // response below instead of reimplementing the split algorithm in JS
  // (the backend is the single source of truth for that math).
  const participantSpendingSummary = useMemo(() => {
    const owedByParticipant = new Map(
      dashboard?.owed_by_person.map((item) => [item.participant_id, item.amount]) ?? [],
    );
    const netBalanceByParticipant = new Map(
      dashboard?.net_balances.map((item) => [item.participant_id, item.balance]) ?? [],
    );

    return (trip?.participants ?? []).map((participant) => {
      const paid = new Map<CurrencyCode, number>();
      const personal = new Map<CurrencyCode, number>();

      for (const expense of trip?.expenses ?? []) {
        if (expense.paid_by !== participant.id) continue;

        const expenseCurrency = normalizeCurrency(expense.currency);
        paid.set(expenseCurrency, (paid.get(expenseCurrency) ?? 0) + expense.amount);

        if (getExpenseType(expense) === "personal") {
          personal.set(
            expenseCurrency,
            (personal.get(expenseCurrency) ?? 0) + expense.amount,
          );
        }
      }

      const toMoneyList = (source: Map<CurrencyCode, number>) =>
        currencies
          .map((item) => ({
            currency: item.code,
            amount: source.get(item.code) ?? 0,
          }))
          .filter((item) => item.amount > 0);

      const owedAmount = owedByParticipant.get(participant.id) ?? 0;
      const netBalance = netBalanceByParticipant.get(participant.id) ?? 0;

      return {
        participant,
        paid: toMoneyList(paid),
        personal: toMoneyList(personal),
        sharedResponsibility:
          settlementCurrency !== null
            ? [{ currency: settlementCurrency, amount: owedAmount }].filter(
                (item) => item.amount > 0,
              )
            : [],
        netBalances:
          settlementCurrency !== null
            ? [{ currency: settlementCurrency, amount: netBalance }]
            : [],
      };
    });
  }, [trip, dashboard, settlementCurrency]);

  async function addParticipant(name: string): Promise<void> {
    if (!tripId || !name.trim()) return;

    setIsSaving(true);
    setError(null);
    try {
      await createParticipant(tripId, { name: name.trim() });
      await loadTrip(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add participant");
    } finally {
      setIsSaving(false);
    }
  }

  async function inviteMember(email: string): Promise<boolean> {
    if (!tripId || !email.trim()) return false;

    setIsSaving(true);
    setError(null);
    try {
      await inviteParticipant(tripId, { email: email.trim() });
      await loadTrip(false);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to invite that person");
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function renameTrip(payload: TripUpdate): Promise<boolean> {
    if (!tripId) return false;

    setIsSaving(true);
    setError(null);
    try {
      await updateTrip(tripId, payload);
      await loadTrip(false);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update trip");
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function removeTrip(): Promise<boolean> {
    if (!tripId) return false;

    setIsSaving(true);
    setError(null);
    try {
      await deleteTrip(tripId);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete trip");
      return false;
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
      await loadTrip(false);
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
      await loadTrip(false);
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
    inviteMember,
    removeParticipant,
    saveExpense,
    removeExpense,
    renameTrip,
    removeTrip,
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
