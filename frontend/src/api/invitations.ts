import { apiRequest } from "./client";
import type { Participant, PendingInvitation } from "../types";

export function getMyInvitations(): Promise<PendingInvitation[]> {
  return apiRequest<PendingInvitation[]>("/invitations");
}

export function acceptInvitation(invitationId: string): Promise<Participant> {
  return apiRequest<Participant>(`/invitations/${invitationId}/accept`, {
    method: "POST",
  });
}

export function declineInvitation(invitationId: string): Promise<void> {
  return apiRequest<void>(`/invitations/${invitationId}`, {
    method: "DELETE",
  });
}
