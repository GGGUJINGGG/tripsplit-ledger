import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, Pencil, Plus, Save, Trash2, X } from "lucide-react";

import { createExpense, deleteExpense, updateExpense } from "../api/expenses";
import { createParticipant, deleteParticipant } from "../api/participants";
import { getSettlements } from "../api/settlements";
import { getTrip } from "../api/trips";
import type { Expense, ExpenseCategory, ExpenseType, Settlement, Trip } from "../types";

const categories: ExpenseCategory[] = [
  "food",
  "hotel",
  "transportation",
  "gas",
  "tickets",
  "shopping",
  "other",
];

const currencies = [
  { code: "USD", label: "USD (US Dollar)" },
  { code: "CNY", label: "CNY (Chinese Yuan)" },
  { code: "EUR", label: "EUR (Euro)" },
  { code: "GBP", label: "GBP (British Pound)" },
] as const;

type CurrencyCode = (typeof currencies)[number]["code"];
type ExpenseSortOption = "newest" | "oldest" | "highest" | "lowest";
type ExpenseTypeFilter = "all" | ExpenseType;

function normalizeCurrency(currency?: string | null): CurrencyCode {
  const normalized = currency?.toUpperCase();
  return currencies.some((item) => item.code === normalized)
    ? (normalized as CurrencyCode)
    : "USD";
}

function formatMoney(currency: string, amount: number): string {
  return `${currency} ${amount.toFixed(2)}`;
}

function formatMoneyItems(items: Array<{ currency: string; amount: number }>): string {
  if (items.length === 0) {
    return "USD 0.00";
  }
  return items.map((item) => formatMoney(item.currency, item.amount)).join(", ");
}

function formatSignedMoney(currency: string, amount: number): string {
  const sign = amount > 0 ? "+" : amount < 0 ? "-" : "";
  return `${sign}${formatMoney(currency, Math.abs(amount))}`;
}

function getExpenseType(expense: Expense): ExpenseType {
  return expense.expense_type ?? "shared";
}

function escapeCsvCell(value: string | number): string {
  const stringValue = String(value);
  if (
    stringValue.includes(",") ||
    stringValue.includes('"') ||
    stringValue.includes("\n")
  ) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

export default function TripDetailPage() {
  const { tripId } = useParams();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [participantName, setParticipantName] = useState("");
  const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);
  const [expenseTitle, setExpenseTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [paidBy, setPaidBy] = useState("");
  const [splitAmong, setSplitAmong] = useState<string[]>([]);
  const [expenseType, setExpenseType] = useState<ExpenseType>("shared");
  const [category, setCategory] = useState<ExpenseCategory>("food");
  const [expenseDate, setExpenseDate] = useState("");
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [note, setNote] = useState("");
  const [filterCategory, setFilterCategory] = useState<ExpenseCategory | "all">("all");
  const [filterPaidBy, setFilterPaidBy] = useState("all");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [expenseSearch, setExpenseSearch] = useState("");
  const [expenseSort, setExpenseSort] = useState<ExpenseSortOption>("newest");
  const [expenseTypeFilter, setExpenseTypeFilter] = useState<ExpenseTypeFilter>("all");
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
      if (!paidBy && nextTrip.participants[0]) {
        setPaidBy(nextTrip.participants[0].id);
      }
      if (splitAmong.length === 0 && nextTrip.participants.length > 0) {
        setSplitAmong(nextTrip.participants.map((participant) => participant.id));
      }
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
  }, [tripId]);

  const participantNames = useMemo(() => {
    return new Map(
      trip?.participants.map((participant) => [participant.id, participant.name]) ?? [],
    );
  }, [trip]);

  const spendingByCurrency = useMemo(() => {
    const totals = new Map<CurrencyCode, number>();

    for (const expense of trip?.expenses ?? []) {
      const expenseCurrency = normalizeCurrency(expense.currency);
      totals.set(expenseCurrency, (totals.get(expenseCurrency) ?? 0) + expense.amount);
    }

    return currencies
      .map((item) => ({
        currency: item.code,
        amount: totals.get(item.code) ?? 0,
      }))
      .filter((item) => item.amount > 0);
  }, [trip]);

  const sharedSpendingByCurrency = useMemo(() => {
    const totals = new Map<CurrencyCode, number>();

    for (const expense of trip?.expenses ?? []) {
      if (getExpenseType(expense) !== "shared") {
        continue;
      }
      const expenseCurrency = normalizeCurrency(expense.currency);
      totals.set(expenseCurrency, (totals.get(expenseCurrency) ?? 0) + expense.amount);
    }

    return currencies
      .map((item) => ({
        currency: item.code,
        amount: totals.get(item.code) ?? 0,
      }))
      .filter((item) => item.amount > 0);
  }, [trip]);

  const personalSpendingByCurrency = useMemo(() => {
    const totals = new Map<CurrencyCode, number>();

    for (const expense of trip?.expenses ?? []) {
      if (getExpenseType(expense) !== "personal") {
        continue;
      }
      const expenseCurrency = normalizeCurrency(expense.currency);
      totals.set(expenseCurrency, (totals.get(expenseCurrency) ?? 0) + expense.amount);
    }

    return currencies
      .map((item) => ({
        currency: item.code,
        amount: totals.get(item.code) ?? 0,
      }))
      .filter((item) => item.amount > 0);
  }, [trip]);

  const averageSpendingByCurrency = useMemo(() => {
    const participantCount = trip?.participants.length ?? 0;
    if (participantCount === 0) {
      return [];
    }

    return spendingByCurrency.map((item) => ({
      currency: item.currency,
      amount: item.amount / participantCount,
    }));
  }, [spendingByCurrency, trip]);

  const filteredExpenses = useMemo(() => {
    const normalizedSearch = expenseSearch.trim().toLowerCase();

    return (trip?.expenses ?? [])
      .filter((expense) => {
        const matchesCategory =
          filterCategory === "all" || expense.category === filterCategory;
        const matchesExpenseType =
          expenseTypeFilter === "all" || getExpenseType(expense) === expenseTypeFilter;
        const matchesPaidBy =
          filterPaidBy === "all" || expense.paid_by === filterPaidBy;
        const matchesStartDate = !filterStartDate || expense.date >= filterStartDate;
        const matchesEndDate = !filterEndDate || expense.date <= filterEndDate;
        const searchableText = `${expense.title} ${expense.note ?? ""}`.toLowerCase();
        const matchesSearch =
          !normalizedSearch || searchableText.includes(normalizedSearch);

        return (
          matchesCategory &&
          matchesExpenseType &&
          matchesPaidBy &&
          matchesStartDate &&
          matchesEndDate &&
          matchesSearch
        );
      })
      .sort((first, second) => {
        if (expenseSort === "highest") {
          return second.amount - first.amount;
        }
        if (expenseSort === "lowest") {
          return first.amount - second.amount;
        }

        const dateComparison = first.date.localeCompare(second.date);
        if (dateComparison !== 0) {
          return expenseSort === "oldest" ? dateComparison : -dateComparison;
        }

        const createdComparison = first.created_at.localeCompare(second.created_at);
        return expenseSort === "oldest" ? createdComparison : -createdComparison;
      });
  }, [
    expenseSearch,
    expenseSort,
    expenseTypeFilter,
    filterCategory,
    filterEndDate,
    filterPaidBy,
    filterStartDate,
    trip,
  ]);

  const categorySummary = useMemo(() => {
    const totals = new Map<
      string,
      {
        category: ExpenseCategory;
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

  const hasActiveFilters =
    filterCategory !== "all" ||
    filterPaidBy !== "all" ||
    expenseTypeFilter !== "all" ||
    Boolean(filterStartDate) ||
    Boolean(filterEndDate) ||
    Boolean(expenseSearch.trim());

  function resetExpenseForm(sourceTrip = trip) {
    setEditingExpenseId(null);
    setExpenseTitle("");
    setAmount("");
    setExpenseType("shared");
    setCategory("food");
    setExpenseDate("");
    setCurrency("USD");
    setNote("");
    if (sourceTrip?.participants[0]) {
      setPaidBy(sourceTrip.participants[0].id);
      setSplitAmong(sourceTrip.participants.map((participant) => participant.id));
    } else {
      setPaidBy("");
      setSplitAmong([]);
    }
  }

  function startEditingExpense(expense: Expense) {
    setEditingExpenseId(expense.id);
    setExpenseTitle(expense.title);
    setAmount(String(expense.amount));
    setPaidBy(expense.paid_by);
    setSplitAmong(expense.split_among);
    setExpenseType(getExpenseType(expense));
    setCategory(expense.category);
    setExpenseDate(expense.date);
    setCurrency(normalizeCurrency(expense.currency));
    setNote(expense.note ?? "");
    setError(null);
  }

  async function handleAddParticipant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tripId || !participantName.trim()) return;

    setIsSaving(true);
    setError(null);
    try {
      await createParticipant(tripId, { name: participantName.trim() });
      setParticipantName("");
      await loadTrip();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add participant");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteParticipant(participantId: string) {
    if (!tripId) return;

    const participantName = trip?.participants.find((p) => p.id === participantId)?.name ?? "this participant";
    const shouldDelete = window.confirm(`Remove ${participantName}? This cannot be undone.`);
    if (!shouldDelete) return;

    setIsSaving(true);
    setError(null);
    try {
      await deleteParticipant(tripId, participantId);
      setSplitAmong((current) => current.filter((id) => id !== participantId));
      if (paidBy === participantId) {
        setPaidBy("");
      }
      await loadTrip();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove participant");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tripId) return;

    const parsedAmount = Number(amount);
    if (!expenseTitle.trim()) {
      setError("Title is required.");
      return;
    }
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setError("Amount must be greater than 0.");
      return;
    }
    if (!paidBy) {
      setError("Paid by is required.");
      return;
    }
    if (expenseType === "shared" && splitAmong.length === 0) {
      setError("Select at least one person to share this expense.");
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const responsibleParticipants =
        expenseType === "personal" ? [paidBy] : splitAmong;
      const payload = {
        title: expenseTitle.trim(),
        amount: parsedAmount,
        paid_by: paidBy,
        split_among: responsibleParticipants,
        expense_type: expenseType,
        category,
        date: expenseDate || new Date().toISOString().slice(0, 10),
        currency,
        note: note.trim() || undefined,
      };

      if (editingExpenseId) {
        await updateExpense(tripId, editingExpenseId, payload);
      } else {
        await createExpense(tripId, payload);
      }

      const refreshedTrip = await loadTrip(false);
      resetExpenseForm(refreshedTrip ?? trip);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save expense");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteExpense(expense: Expense) {
    if (!tripId) return;

    const shouldDelete = window.confirm(
      `Delete "${expense.title}"? This cannot be undone.`,
    );
    if (!shouldDelete) {
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      await deleteExpense(tripId, expense.id);
      if (editingExpenseId === expense.id) {
        resetExpenseForm();
      }
      await loadTrip();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete expense");
    } finally {
      setIsSaving(false);
    }
  }

  function toggleSplitParticipant(participantId: string) {
    setSplitAmong((current) =>
      current.includes(participantId)
        ? current.filter((id) => id !== participantId)
        : [...current, participantId],
    );
  }

  function clearExpenseFilters() {
    setFilterCategory("all");
    setFilterPaidBy("all");
    setExpenseTypeFilter("all");
    setFilterStartDate("");
    setFilterEndDate("");
    setExpenseSearch("");
  }

  function handleExportCsv() {
    if (!trip) return;

    const rows = filteredExpenses.map((expense) => [
      expense.date,
      expense.title,
      getExpenseType(expense) === "shared" ? "Shared" : "Personal",
      expense.category,
      participantNames.get(expense.paid_by) ?? "Unknown",
      expense.split_among
        .map((participantId) => participantNames.get(participantId) ?? "Unknown")
        .join("; "),
      normalizeCurrency(expense.currency),
      expense.amount.toFixed(2),
      expense.note ?? "",
    ]);
    const csv = [
      [
        "Date",
        "Title",
        "Type",
        "Category",
        "Paid By",
        "Split Among",
        "Currency",
        "Amount",
        "Note",
      ],
      ...rows,
    ]
      .map((row) => row.map(escapeCsvCell).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${trip.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-expenses.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (isLoading) {
    return <p className="empty-state">Loading trip...</p>;
  }

  if (!trip) {
    return (
      <section className="page-stack">
        <div className="alert">{error ?? "Trip not found"}</div>
      </section>
    );
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Trip Detail</p>
          <h1>{trip.name}</h1>
          <p className="muted">
            {trip.start_date}
            {trip.end_date ? ` to ${trip.end_date}` : ""}
          </p>
        </div>
        <Link className="secondary-button" to={`/trips/${trip.id}/settlements`}>
          Settlements
        </Link>
      </header>

      {error ? <div className="alert">{error}</div> : null}

      <div className="summary-row">
        <div className="metric-card">
          <span>Total spending</span>
          {spendingByCurrency.length === 0 ? (
            <strong>USD 0.00</strong>
          ) : (
            <div className="metric-list">
              {spendingByCurrency.map((item) => (
                <strong key={item.currency}>
                  {formatMoney(item.currency, item.amount)}
                </strong>
              ))}
            </div>
          )}
        </div>
        <div className="metric-card">
          <span>Shared spending</span>
          {sharedSpendingByCurrency.length === 0 ? (
            <strong>USD 0.00</strong>
          ) : (
            <div className="metric-list">
              {sharedSpendingByCurrency.map((item) => (
                <strong key={item.currency}>
                  {formatMoney(item.currency, item.amount)}
                </strong>
              ))}
            </div>
          )}
        </div>
        <div className="metric-card">
          <span>Personal spending</span>
          {personalSpendingByCurrency.length === 0 ? (
            <strong>USD 0.00</strong>
          ) : (
            <div className="metric-list">
              {personalSpendingByCurrency.map((item) => (
                <strong key={item.currency}>
                  {formatMoney(item.currency, item.amount)}
                </strong>
              ))}
            </div>
          )}
        </div>
        <div className="metric-card">
          <span>Participants</span>
          <strong>{trip.participants.length}</strong>
        </div>
        <div className="metric-card">
          <span>Expenses</span>
          <strong>{trip.expenses.length}</strong>
        </div>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <h2>Participant Spending</h2>
          <span className="muted">{participantSpendingSummary.length} people</span>
        </div>
        {participantSpendingSummary.length === 0 ? (
          <p className="empty-state">Add participants to see spending summaries.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Participant</th>
                  <th>Total Paid</th>
                  <th>Shared Responsibility</th>
                  <th>Personal Spending</th>
                  <th>Net Balance</th>
                </tr>
              </thead>
              <tbody>
                {participantSpendingSummary.map((item) => (
                  <tr key={item.participant.id}>
                    <td>
                      <strong>{item.participant.name}</strong>
                    </td>
                    <td>{formatMoneyItems(item.paid)}</td>
                    <td>{formatMoneyItems(item.sharedResponsibility)}</td>
                    <td>{formatMoneyItems(item.personal)}</td>
                    <td>
                      {item.netBalances.length === 0
                        ? "USD 0.00"
                        : settlementCurrency === null
                          ? "Mixed currencies"
                          : item.netBalances
                              .map((balance) =>
                                formatSignedMoney(balance.currency, balance.amount),
                              )
                              .join(", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Settlement Summary</h2>
          <Link className="table-link" to={`/trips/${trip.id}/settlements`}>
            View full page
          </Link>
        </div>
        {settlements.length === 0 ? (
          <p className="empty-state">Everyone is settled.</p>
        ) : settlementCurrency === null ? (
          <p className="empty-state">
            Settlements are hidden for mixed-currency trips until exchange-rate
            conversion is supported.
          </p>
        ) : (
          <div className="settlement-list">
            {settlements.map((settlement) => (
              <div
                className="settlement-row"
                key={`${settlement.from_participant_id}-${settlement.to_participant_id}`}
              >
                <span>
                  <strong>{settlement.from_name}</strong> pays{" "}
                  <strong>{settlement.to_name}</strong>
                </span>
                <strong>{formatMoney(settlementCurrency, settlement.amount)}</strong>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="content-grid two-columns">
        <section className="panel">
          <div className="panel-heading">
            <h2>Participants</h2>
          </div>
          <form className="inline-form" onSubmit={handleAddParticipant}>
            <input
              value={participantName}
              onChange={(event) => setParticipantName(event.target.value)}
              placeholder="Name"
            />
            <button className="icon-button" type="submit" disabled={isSaving} title="Add participant">
              <Plus size={18} />
            </button>
          </form>
          <div className="list-stack">
            {trip.participants.length === 0 ? (
              <p className="empty-state">Add participants before recording expenses.</p>
            ) : (
              trip.participants.map((participant) => (
                <div className="list-row" key={participant.id}>
                  <span>{participant.name}</span>
                  <button
                    className="ghost-icon-button"
                    type="button"
                    onClick={() => void handleDeleteParticipant(participant.id)}
                    disabled={isSaving}
                    title="Remove participant"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>{editingExpenseId ? "Edit Expense" : "Add Expense"}</h2>
            {editingExpenseId ? (
              <button
                className="secondary-button"
                type="button"
                onClick={() => resetExpenseForm()}
                disabled={isSaving}
              >
                <X size={16} />
                Cancel
              </button>
            ) : null}
          </div>
          <form className="form-grid compact" onSubmit={handleSaveExpense}>
            <label htmlFor="expense-title">
              Title
              <input
                id="expense-title"
                value={expenseTitle}
                onChange={(event) => setExpenseTitle(event.target.value)}
                placeholder="Dinner"
              />
            </label>
            <label htmlFor="expense-amount">
              Amount
              <input
                id="expense-amount"
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="80.00"
              />
            </label>
            <label htmlFor="expense-paid-by">
              Paid by
              <select
                id="expense-paid-by"
                value={paidBy}
                onChange={(event) => {
                  const nextPaidBy = event.target.value;
                  setPaidBy(nextPaidBy);
                  if (expenseType === "personal" && nextPaidBy) {
                    setSplitAmong([nextPaidBy]);
                  }
                }}
              >
                <option value="">Select payer</option>
                {trip.participants.map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.name}
                  </option>
                ))}
              </select>
            </label>
            <label htmlFor="expense-type">
              Type
              <select
                id="expense-type"
                value={expenseType}
                onChange={(event) => {
                  const nextType = event.target.value as ExpenseType;
                  setExpenseType(nextType);
                  if (nextType === "personal" && paidBy) {
                    setSplitAmong([paidBy]);
                  }
                }}
              >
                <option value="shared">Shared</option>
                <option value="personal">Personal</option>
              </select>
            </label>
            <label htmlFor="expense-category">
              Category
              <select
                id="expense-category"
                value={category}
                onChange={(event) => setCategory(event.target.value as ExpenseCategory)}
              >
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label htmlFor="expense-date">
              Date
              <input
                id="expense-date"
                type="date"
                value={expenseDate}
                onChange={(event) => setExpenseDate(event.target.value)}
              />
              <span className="field-hint">Stored as YYYY-MM-DD.</span>
            </label>
            <label htmlFor="expense-currency">
              Currency
              <select
                id="expense-currency"
                value={currency}
                onChange={(event) => setCurrency(event.target.value as CurrencyCode)}
              >
                {currencies.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="wide-field" htmlFor="expense-note">
              Note
              <input
                id="expense-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Optional"
              />
            </label>
            <fieldset className="wide-field checkbox-field">
              <legend>Who should share this expense?</legend>
              {expenseType === "personal" ? (
                <p className="helper-text">
                  Personal expenses are assigned only to the payer and do not affect
                  settlements.
                </p>
              ) : (
                <>
                  <p className="helper-text">
                    The amount is split evenly across the selected people. The payer gets
                    credit for paying upfront, and each selected person owes their share.
                  </p>
                  <div className="checkbox-grid">
                    {trip.participants.map((participant) => (
                      <label key={participant.id}>
                        <input
                          type="checkbox"
                          checked={splitAmong.includes(participant.id)}
                          onChange={() => toggleSplitParticipant(participant.id)}
                        />
                        {participant.name}
                      </label>
                    ))}
                  </div>
                </>
              )}
            </fieldset>
            <div className="form-actions wide-field">
              <button className="primary-button" type="submit" disabled={isSaving}>
                {editingExpenseId ? <Save size={18} /> : <Plus size={18} />}
                {editingExpenseId ? "Save changes" : "Add expense"}
              </button>
            </div>
          </form>
        </section>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <h2>Category Summary</h2>
          <span className="muted">{categorySummary.length} categories</span>
        </div>
        {categorySummary.length === 0 ? (
          <p className="empty-state">No category spending yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Shared</th>
                  <th>Personal</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {categorySummary.map((item) => (
                  <tr key={`${item.category}-${item.currency}`}>
                    <td>{item.category}</td>
                    <td>{formatMoney(item.currency, item.shared)}</td>
                    <td>{formatMoney(item.currency, item.personal)}</td>
                    <td>{formatMoney(item.currency, item.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Expense Ledger</h2>
          <div className="panel-actions">
            <span className="muted">
              Showing {filteredExpenses.length} of {trip.expenses.length}
            </span>
            <button
              className="secondary-button"
              type="button"
              onClick={handleExportCsv}
              disabled={filteredExpenses.length === 0}
            >
              <Download size={16} />
              Export CSV
            </button>
          </div>
        </div>
        <div className="filter-grid">
          <label htmlFor="expense-search">
            Search
            <input
              id="expense-search"
              value={expenseSearch}
              onChange={(event) => setExpenseSearch(event.target.value)}
              placeholder="Title or note"
            />
          </label>
          <label htmlFor="filter-category">
            Category
            <select
              id="filter-category"
              value={filterCategory}
              onChange={(event) =>
                setFilterCategory(event.target.value as ExpenseCategory | "all")
              }
            >
              <option value="all">All categories</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor="filter-paid-by">
            Paid by
            <select
              id="filter-paid-by"
              value={filterPaidBy}
              onChange={(event) => setFilterPaidBy(event.target.value)}
            >
              <option value="all">Everyone</option>
              {trip.participants.map((participant) => (
                <option key={participant.id} value={participant.id}>
                  {participant.name}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor="filter-expense-type">
            Type
            <select
              id="filter-expense-type"
              value={expenseTypeFilter}
              onChange={(event) =>
                setExpenseTypeFilter(event.target.value as ExpenseTypeFilter)
              }
            >
              <option value="all">All Expenses</option>
              <option value="shared">Shared Expenses</option>
              <option value="personal">Personal Expenses</option>
            </select>
          </label>
          <label htmlFor="expense-sort">
            Sort
            <select
              id="expense-sort"
              value={expenseSort}
              onChange={(event) =>
                setExpenseSort(event.target.value as ExpenseSortOption)
              }
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="highest">Highest Amount</option>
              <option value="lowest">Lowest Amount</option>
            </select>
          </label>
          <label htmlFor="filter-start-date">
            From date
            <input
              id="filter-start-date"
              value={filterStartDate}
              onChange={(event) => setFilterStartDate(event.target.value)}
              placeholder="2026-07-01"
            />
          </label>
          <label htmlFor="filter-end-date">
            To date
            <input
              id="filter-end-date"
              value={filterEndDate}
              onChange={(event) => setFilterEndDate(event.target.value)}
              placeholder="2026-07-04"
            />
          </label>
          <div className="filter-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={clearExpenseFilters}
              disabled={!hasActiveFilters}
            >
              Clear filters
            </button>
          </div>
        </div>
        {trip.expenses.length === 0 ? (
          <p className="empty-state">No expenses yet.</p>
        ) : filteredExpenses.length === 0 ? (
          <p className="empty-state">No expenses match the current filters.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Amount</th>
                  <th>Paid By</th>
                  <th>Type</th>
                  <th>Category</th>
                  <th>Date</th>
                  <th>Split</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredExpenses.map((expense) => (
                  <tr key={expense.id}>
                    <td>
                      <strong>{expense.title}</strong>
                      {expense.note ? <span className="cell-note">{expense.note}</span> : null}
                    </td>
                    <td>
                      {formatMoney(normalizeCurrency(expense.currency), expense.amount)}
                    </td>
                    <td>{participantNames.get(expense.paid_by) ?? "Unknown"}</td>
                    <td>{getExpenseType(expense) === "shared" ? "Shared" : "Personal"}</td>
                    <td>{expense.category}</td>
                    <td>{expense.date}</td>
                    <td>
                      {expense.split_among
                        .map((participantId) => participantNames.get(participantId) ?? "Unknown")
                        .join(", ")}
                    </td>
                    <td className="actions-cell">
                      <button
                        className="table-action-button"
                        type="button"
                        onClick={() => startEditingExpense(expense)}
                        disabled={isSaving}
                        title="Edit expense"
                      >
                        <Pencil size={16} />
                        Edit
                      </button>
                      <button
                        className="table-action-button danger"
                        type="button"
                        onClick={() => void handleDeleteExpense(expense)}
                        disabled={isSaving}
                        title="Delete expense"
                      >
                        <Trash2 size={16} />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
