import { apiRequest } from "./client";
import type { Participant, ParticipantCreate, ParticipantInvite } from "../types";

export function createParticipant(
  tripId: string,
  payload: ParticipantCreate,
): Promise<Participant> {
  return apiRequest<Participant>(`/trips/${tripId}/participants`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function inviteParticipant(
  tripId: string,
  payload: ParticipantInvite,
): Promise<Participant> {
  return apiRequest<Participant>(`/trips/${tripId}/participants/invite`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteParticipant(
  tripId: string,
  participantId: string,
): Promise<void> {
  return apiRequest<void>(`/trips/${tripId}/participants/${participantId}`, {
    method: "DELETE",
  });
}
