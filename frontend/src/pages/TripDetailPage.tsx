import { useState } from "react";
import { useParams } from "react-router-dom";

import CategoryBreakdown from "../components/trip/CategoryBreakdown";
import DashboardSummary from "../components/trip/DashboardSummary";
import ExpenseForm from "../components/trip/ExpenseForm";
import ExpenseTable from "../components/trip/ExpenseTable";
import ParticipantsPanel from "../components/trip/ParticipantsPanel";
import ParticipantSummary from "../components/trip/ParticipantSummary";
import SettlementPanel from "../components/trip/SettlementPanel";
import TripHeader from "../components/trip/TripHeader";
import { useExpenseFilters } from "../hooks/useExpenseFilters";
import { useTripDetail } from "../hooks/useTripDetail";
import type { Expense } from "../types";
import { downloadExpensesCsv } from "../utils/expenses";

export default function TripDetailPage() {
  const { tripId } = useParams();
  const {
    trip,
    settlements,
    isLoading,
    isSaving,
    error,
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
  } = useTripDetail(tripId);

  const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);
  const filters = useExpenseFilters(trip?.expenses ?? []);

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

  const editingExpense = trip.expenses.find((expense) => expense.id === editingExpenseId) ?? null;

  async function handleSaveExpense(payload: Parameters<typeof saveExpense>[0]): Promise<boolean> {
    const refreshedTrip = await saveExpense(payload, editingExpenseId);
    if (refreshedTrip) {
      setEditingExpenseId(null);
      return true;
    }
    return false;
  }

  async function handleDeleteExpense(expense: Expense) {
    const shouldDelete = window.confirm(`Delete "${expense.title}"? This cannot be undone.`);
    if (!shouldDelete) return;

    const succeeded = await removeExpense(expense);
    if (succeeded && editingExpenseId === expense.id) {
      setEditingExpenseId(null);
    }
  }

  function handleExportCsv() {
    if (!trip) return;
    downloadExpensesCsv(trip.name, filters.filteredExpenses, participantNames);
  }

  return (
    <section className="page-stack">
      <TripHeader trip={trip} />

      {error ? <div className="alert">{error}</div> : null}

      <DashboardSummary
        trip={trip}
        spendingByCurrency={spendingByCurrency}
        sharedSpendingByCurrency={sharedSpendingByCurrency}
        personalSpendingByCurrency={personalSpendingByCurrency}
      />

      <ParticipantSummary
        summary={participantSpendingSummary}
        settlementCurrency={settlementCurrency}
      />

      <SettlementPanel
        tripId={trip.id}
        settlements={settlements}
        settlementCurrency={settlementCurrency}
      />

      <div className="content-grid two-columns">
        <ParticipantsPanel
          participants={trip.participants}
          isSaving={isSaving}
          onAdd={addParticipant}
          onRemove={removeParticipant}
        />

        <ExpenseForm
          participants={trip.participants}
          editingExpense={editingExpense}
          isSaving={isSaving}
          onCancelEdit={() => setEditingExpenseId(null)}
          onSubmit={handleSaveExpense}
        />
      </div>

      <CategoryBreakdown categorySummary={categorySummary} />

      <ExpenseTable
        totalExpenseCount={trip.expenses.length}
        participants={trip.participants}
        participantNames={participantNames}
        filters={filters}
        isSaving={isSaving}
        onEdit={(expense) => setEditingExpenseId(expense.id)}
        onDelete={handleDeleteExpense}
        onExportCsv={handleExportCsv}
      />
    </section>
  );
}
