import { apiRequest } from "./client";
import type { Trip, TripCreate, TripUpdate } from "../types";

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

export function updateTrip(tripId: string, payload: TripUpdate): Promise<Trip> {
  return apiRequest<Trip>(`/trips/${tripId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteTrip(tripId: string): Promise<void> {
  return apiRequest<void>(`/trips/${tripId}`, {
    method: "DELETE",
  });
}
