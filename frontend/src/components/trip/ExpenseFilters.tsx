import type { useExpenseFilters } from "../../hooks/useExpenseFilters";
import type { ExpenseCategory, Participant } from "../../types";
import { categories } from "../../utils/expenses";

interface ExpenseFiltersProps {
  participants: Participant[];
  filters: ReturnType<typeof useExpenseFilters>;
}

export default function ExpenseFilters({ participants, filters }: ExpenseFiltersProps) {
  return (
    <div className="filter-grid">
      <label htmlFor="expense-search">
        Search
        <input
          id="expense-search"
          value={filters.expenseSearch}
          onChange={(event) => filters.setExpenseSearch(event.target.value)}
          placeholder="Title or note"
        />
      </label>
      <label htmlFor="filter-category">
        Category
        <select
          id="filter-category"
          value={filters.filterCategory}
          onChange={(event) =>
            filters.setFilterCategory(event.target.value as ExpenseCategory | "all")
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
          value={filters.filterPaidBy}
          onChange={(event) => filters.setFilterPaidBy(event.target.value)}
        >
          <option value="all">Everyone</option>
          {participants.map((participant) => (
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
          value={filters.expenseTypeFilter}
          onChange={(event) =>
            filters.setExpenseTypeFilter(
              event.target.value as typeof filters.expenseTypeFilter,
            )
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
          value={filters.expenseSort}
          onChange={(event) =>
            filters.setExpenseSort(event.target.value as typeof filters.expenseSort)
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
          value={filters.filterStartDate}
          onChange={(event) => filters.setFilterStartDate(event.target.value)}
          placeholder="2026-07-01"
        />
      </label>
      <label htmlFor="filter-end-date">
        To date
        <input
          id="filter-end-date"
          value={filters.filterEndDate}
          onChange={(event) => filters.setFilterEndDate(event.target.value)}
          placeholder="2026-07-04"
        />
      </label>
      <div className="filter-actions">
        <button
          className="secondary-button"
          type="button"
          onClick={filters.clearFilters}
          disabled={!filters.hasActiveFilters}
        >
          Clear filters
        </button>
      </div>
    </div>
  );
}
