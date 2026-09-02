import type { Expense, ExpenseCategory, ExpenseType } from "../types";
import { normalizeCurrency } from "./currency";

export const categories: ExpenseCategory[] = [
  "food",
  "hotel",
  "transportation",
  "gas",
  "tickets",
  "shopping",
  "other",
];

export function getExpenseType(expense: Expense): ExpenseType {
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

export function downloadExpensesCsv(
  tripName: string,
  expenses: Expense[],
  participantNames: Map<string, string>,
): void {
  const rows = expenses.map((expense) => [
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
  link.download = `${tripName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-expenses.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
