import { useMemo, useState } from "react";

import type { Expense, ExpenseCategory, ExpenseType } from "../types";
import { getExpenseType } from "../utils/expenses";

export type ExpenseSortOption = "newest" | "oldest" | "highest" | "lowest";
export type ExpenseTypeFilter = "all" | ExpenseType;

export function useExpenseFilters(expenses: Expense[]) {
  const [filterCategory, setFilterCategory] = useState<ExpenseCategory | "all">("all");
  const [filterPaidBy, setFilterPaidBy] = useState("all");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [expenseSearch, setExpenseSearch] = useState("");
  const [expenseSort, setExpenseSort] = useState<ExpenseSortOption>("newest");
  const [expenseTypeFilter, setExpenseTypeFilter] = useState<ExpenseTypeFilter>("all");

  const filteredExpenses = useMemo(() => {
    const normalizedSearch = expenseSearch.trim().toLowerCase();

    return expenses
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
    expenses,
    expenseSearch,
    expenseSort,
    expenseTypeFilter,
    filterCategory,
    filterEndDate,
    filterPaidBy,
    filterStartDate,
  ]);

  const hasActiveFilters =
    filterCategory !== "all" ||
    filterPaidBy !== "all" ||
    expenseTypeFilter !== "all" ||
    Boolean(filterStartDate) ||
    Boolean(filterEndDate) ||
    Boolean(expenseSearch.trim());

  function clearFilters() {
    setFilterCategory("all");
    setFilterPaidBy("all");
    setExpenseTypeFilter("all");
    setFilterStartDate("");
    setFilterEndDate("");
    setExpenseSearch("");
  }

  return {
    filterCategory,
    setFilterCategory,
    filterPaidBy,
    setFilterPaidBy,
    filterStartDate,
    setFilterStartDate,
    filterEndDate,
    setFilterEndDate,
    expenseSearch,
    setExpenseSearch,
    expenseSort,
    setExpenseSort,
    expenseTypeFilter,
    setExpenseTypeFilter,
    filteredExpenses,
    hasActiveFilters,
    clearFilters,
  };
}
