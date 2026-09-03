import { ChevronLeft, ChevronRight, Download, Pencil, Trash2 } from "lucide-react";

import { EXPENSE_PAGE_SIZE, type useExpenseFilters } from "../../hooks/useExpenseFilters";
import type { Expense, Participant } from "../../types";
import { formatMoney, normalizeCurrency } from "../../utils/currency";
import { getExpenseType } from "../../utils/expenses";
import ExpenseFilters from "./ExpenseFilters";

interface ExpenseTableProps {
  totalExpenseCount: number;
  participants: Participant[];
  participantNames: Map<string, string>;
  filters: ReturnType<typeof useExpenseFilters>;
  isSaving: boolean;
  onEdit: (expense: Expense) => void;
  onDelete: (expense: Expense) => void;
  onExportCsv: () => void;
}

export default function ExpenseTable({
  totalExpenseCount,
  participants,
  participantNames,
  filters,
  isSaving,
  onEdit,
  onDelete,
  onExportCsv,
}: ExpenseTableProps) {
  const {
    filteredExpenses,
    paginatedExpenses,
    currentPage,
    setCurrentPage,
    totalPages,
  } = filters;

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Expense Ledger</h2>
        <div className="panel-actions">
          <span className="muted">
            {totalPages > 1
              ? `Showing ${(currentPage - 1) * EXPENSE_PAGE_SIZE + 1}-${
                  (currentPage - 1) * EXPENSE_PAGE_SIZE + paginatedExpenses.length
                } of ${filteredExpenses.length}`
              : `Showing ${filteredExpenses.length} of ${totalExpenseCount}`}
          </span>
          <button
            className="secondary-button"
            type="button"
            onClick={onExportCsv}
            disabled={filteredExpenses.length === 0}
          >
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </div>
      <ExpenseFilters participants={participants} filters={filters} />
      {totalExpenseCount === 0 ? (
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
              {paginatedExpenses.map((expense) => (
                <tr key={expense.id}>
                  <td>
                    <strong>{expense.title}</strong>
                    {expense.note ? <span className="cell-note">{expense.note}</span> : null}
                  </td>
                  <td>{formatMoney(normalizeCurrency(expense.currency), expense.amount)}</td>
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
                      onClick={() => onEdit(expense)}
                      disabled={isSaving}
                      aria-label={`Edit ${expense.title}`}
                      title="Edit expense"
                    >
                      <Pencil size={16} />
                      Edit
                    </button>
                    <button
                      className="table-action-button danger"
                      type="button"
                      onClick={() => onDelete(expense)}
                      disabled={isSaving}
                      aria-label={`Delete ${expense.title}`}
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
      {totalPages > 1 ? (
        <div className="pagination">
          <button
            className="secondary-button"
            type="button"
            onClick={() => setCurrentPage(currentPage - 1)}
            disabled={currentPage <= 1}
          >
            <ChevronLeft size={16} />
            Previous
          </button>
          <span className="muted">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="secondary-button"
            type="button"
            onClick={() => setCurrentPage(currentPage + 1)}
            disabled={currentPage >= totalPages}
          >
            Next
            <ChevronRight size={16} />
          </button>
        </div>
      ) : null}
    </section>
  );
}
