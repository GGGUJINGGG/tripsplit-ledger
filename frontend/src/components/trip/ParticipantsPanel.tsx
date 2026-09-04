import { FormEvent, useState } from "react";
import { Plus, Trash2, UserPlus } from "lucide-react";

import type { Participant } from "../../types";

interface ParticipantsPanelProps {
  participants: Participant[];
  isSaving: boolean;
  onAdd: (name: string) => Promise<void>;
  onInvite: (email: string) => Promise<boolean>;
  onRemove: (participantId: string) => Promise<void>;
}

export default function ParticipantsPanel({
  participants,
  isSaving,
  onAdd,
  onInvite,
  onRemove,
}: ParticipantsPanelProps) {
  const [name, setName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteConfirmation, setInviteConfirmation] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    await onAdd(name);
    setName("");
  }

  async function handleInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!inviteEmail.trim()) return;

    setInviteConfirmation(null);
    const succeeded = await onInvite(inviteEmail);
    if (succeeded) {
      setInviteConfirmation(`Invited ${inviteEmail.trim()} to this trip.`);
      setInviteEmail("");
    }
  }

  async function handleRemove(participant: Participant) {
    const shouldDelete = window.confirm(
      `Remove ${participant.name}? This cannot be undone.`,
    );
    if (!shouldDelete) return;
    await onRemove(participant.id);
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Participants</h2>
      </div>
      <form className="inline-form" onSubmit={handleSubmit}>
        <label htmlFor="participant-name" className="sr-only">
          Participant name
        </label>
        <input
          id="participant-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Name"
        />
        <button
          className="icon-button"
          type="submit"
          disabled={isSaving}
          aria-label="Add participant"
          title="Add participant"
        >
          <Plus size={18} />
        </button>
      </form>
      <div className="list-stack">
        {participants.length === 0 ? (
          <p className="empty-state">Add participants before recording expenses.</p>
        ) : (
          participants.map((participant) => (
            <div className="list-row" key={participant.id}>
              <span>{participant.name}</span>
              <button
                className="ghost-icon-button"
                type="button"
                onClick={() => void handleRemove(participant)}
                disabled={isSaving}
                aria-label={`Remove ${participant.name}`}
                title="Remove participant"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))
        )}
      </div>

      <div className="panel-subsection">
        <p className="field-hint">
          Invite anyone by email — if they don't have a TripSplit account
          yet, they'll get a link to register and be added automatically.
          Only the trip owner can invite new members.
        </p>
        <form className="inline-form" onSubmit={handleInvite}>
          <label htmlFor="invite-email" className="sr-only">
            Invite by email
          </label>
          <input
            id="invite-email"
            type="email"
            value={inviteEmail}
            onChange={(event) => {
              setInviteEmail(event.target.value);
              setInviteConfirmation(null);
            }}
            placeholder="person@example.com"
          />
          <button
            className="icon-button"
            type="submit"
            disabled={isSaving}
            aria-label="Send invite"
            title="Send invite"
          >
            <UserPlus size={18} />
          </button>
        </form>
        {inviteConfirmation ? (
          <p className="field-hint">{inviteConfirmation}</p>
        ) : null}
      </div>
    </section>
  );
}
