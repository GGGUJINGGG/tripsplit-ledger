import { apiRequest } from "./client";
import type { Expense, ExpenseCreate, ExpenseUpdate } from "../types";

export function createExpense(
  tripId: string,
  payload: ExpenseCreate,
): Promise<Expense> {
  return apiRequest<Expense>(`/trips/${tripId}/expenses`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteExpense(tripId: string, expenseId: string): Promise<void> {
  return apiRequest<void>(`/trips/${tripId}/expenses/${expenseId}`, {
    method: "DELETE",
  });
}

export function updateExpense(
  tripId: string,
  expenseId: string,
  payload: ExpenseUpdate,
): Promise<Expense> {
  return apiRequest<Expense>(`/trips/${tripId}/expenses/${expenseId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
