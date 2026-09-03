import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Expense } from "../types";
import { EXPENSE_PAGE_SIZE, useExpenseFilters } from "./useExpenseFilters";

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
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
  }));
}

describe("useExpenseFilters pagination", () => {
  it("shows at most EXPENSE_PAGE_SIZE items on the first page", () => {
    const expenses = buildExpenses(EXPENSE_PAGE_SIZE + 10);
    const { result } = renderHook(() => useExpenseFilters(expenses));

    expect(result.current.currentPage).toBe(1);
    expect(result.current.totalPages).toBe(2);
    expect(result.current.paginatedExpenses).toHaveLength(EXPENSE_PAGE_SIZE);
  });

  it("returns all items on one page when under the page size", () => {
    const expenses = buildExpenses(5);
    const { result } = renderHook(() => useExpenseFilters(expenses));

    expect(result.current.totalPages).toBe(1);
    expect(result.current.paginatedExpenses).toHaveLength(5);
  });

  it("navigates to the next page and shows the remaining items", () => {
    const expenses = buildExpenses(EXPENSE_PAGE_SIZE + 10);
    const { result } = renderHook(() => useExpenseFilters(expenses));

    act(() => {
      result.current.setCurrentPage(2);
    });

    expect(result.current.currentPage).toBe(2);
    expect(result.current.paginatedExpenses).toHaveLength(10);
  });

  it("resets to page 1 when a filter changes", () => {
    const expenses = buildExpenses(EXPENSE_PAGE_SIZE + 10);
    const { result } = renderHook(() => useExpenseFilters(expenses));

    act(() => {
      result.current.setCurrentPage(2);
    });
    expect(result.current.currentPage).toBe(2);

    act(() => {
      result.current.setFilterCategory("hotel");
    });

    expect(result.current.currentPage).toBe(1);
  });

  it("clamps the current page down if the result set shrinks", () => {
    const expenses = buildExpenses(EXPENSE_PAGE_SIZE + 10);
    const { result, rerender } = renderHook(
      ({ items }) => useExpenseFilters(items),
      { initialProps: { items: expenses } },
    );

    act(() => {
      result.current.setCurrentPage(2);
    });
    expect(result.current.currentPage).toBe(2);

    rerender({ items: buildExpenses(3) });

    expect(result.current.currentPage).toBe(1);
    expect(result.current.totalPages).toBe(1);
  });
});
