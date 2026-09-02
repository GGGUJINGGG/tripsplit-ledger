import { apiRequest } from "./client";
import type { DashboardSummary } from "../types";

export function getDashboard(tripId: string): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>(`/trips/${tripId}/dashboard`);
}
