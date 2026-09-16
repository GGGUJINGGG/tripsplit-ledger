import { apiRequest } from "./client";
import type { Payment, PaymentCreate } from "../types";

export function createPayment(
  tripId: string,
  payload: PaymentCreate,
): Promise<Payment> {
  return apiRequest<Payment>(`/trips/${tripId}/payments`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deletePayment(tripId: string, paymentId: string): Promise<void> {
  return apiRequest<void>(`/trips/${tripId}/payments/${paymentId}`, {
    method: "DELETE",
  });
}

export function confirmPayment(tripId: string, paymentId: string): Promise<Payment> {
  return apiRequest<Payment>(`/trips/${tripId}/payments/${paymentId}/confirm`, {
    method: "POST",
  });
}

export function rejectPayment(tripId: string, paymentId: string): Promise<Payment> {
  return apiRequest<Payment>(`/trips/${tripId}/payments/${paymentId}/reject`, {
    method: "POST",
  });
}
