import { apiRequest } from "./client";
import type { SettlementSummary } from "../types";

export function getSettlements(tripId: string): Promise<SettlementSummary> {
  return apiRequest<SettlementSummary>(`/trips/${tripId}/settlements`);
}
