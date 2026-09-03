import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EXPENSE_PAGE_SIZE, useExpenseFilters } from "../../hooks/useExpenseFilters";
import type { Expense, Participant } from "../../types";
import ExpenseTable from "./ExpenseTable";

function buildExpenses(count: number): Expense[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `e${index}`,
    trip_id: "trip-1",
    title: `Expense ${index}`,
    amount: 10,
    paid_by: "p1",
    split_among: ["p1"],
    expense_type: "shared",
    category: "food",
    date: `2026-07-${String((index % 28) + 1).padStart(2, "0")}`,
    currency: "USD",
    note: null,
    created_at: `2026-07-01T00:00:0${index % 9}Z`,
    updated_at: "2026-07-01T00:00:00Z",
  }));
}

const participants: Participant[] = [{ id: "p1", name: "Alex", role: "owner" }];
const participantNames = new Map([["p1", "Alex"]]);

// A thin harness so the hook and the component share one render tree —
// exactly how TripDetailPage wires them together in the real app.
function Harness({ expenseCount }: { expenseCount: number }) {
  const filters = useExpenseFilters(buildExpenses(expenseCount));

  return (
    <ExpenseTable
      totalExpenseCount={expenseCount}
      participants={participants}
      participantNames={participantNames}
      filters={filters}
      isSaving={false}
      onEdit={vi.fn()}
      onDelete={vi.fn()}
      onExportCsv={vi.fn()}
    />
  );
}

describe("ExpenseTable pagination", () => {
  it("does not show pagination controls when everything fits on one page", () => {
    render(<Harness expenseCount={5} />);

    expect(screen.queryByRole("button", { name: /next/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/page \d+ of \d+/i)).not.toBeInTheDocument();
  });

  it("shows only a page's worth of rows and the correct page count", () => {
    render(<Harness expenseCount={EXPENSE_PAGE_SIZE + 10} />);

    const rows = screen.getAllByRole("row");
    // +1 for the header row.
    expect(rows).toHaveLength(EXPENSE_PAGE_SIZE + 1);
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
  });

  it("moves to the next page and shows the remaining rows", async () => {
    const user = userEvent.setup();
    render(<Harness expenseCount={EXPENSE_PAGE_SIZE + 10} />);

    const previousButton = screen.getByRole("button", { name: /previous/i });
    expect(previousButton).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    // Second page has the remaining 10 rows, +1 header row.
    expect(screen.getAllByRole("row")).toHaveLength(11);
  });
});
