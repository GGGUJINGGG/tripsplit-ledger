import { apiRequest } from "./client";
import type { Trip, TripCreate } from "../types";

export function getTrips(): Promise<Trip[]> {
  return apiRequest<Trip[]>("/trips");
}

export function createTrip(payload: TripCreate): Promise<Trip> {
  return apiRequest<Trip>("/trips", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTrip(tripId: string): Promise<Trip> {
  return apiRequest<Trip>(`/trips/${tripId}`);
}
