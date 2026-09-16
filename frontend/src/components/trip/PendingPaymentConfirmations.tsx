import { Check, X } from "lucide-react";

import type { Participant, Payment } from "../../types";
import { formatMoney } from "../../utils/currency";

interface PendingPaymentConfirmationsProps {
  participants: Participant[];
  payments: Payment[];
  currentUserId?: string;
  isSaving: boolean;
  onConfirm: (paymentId: string) => Promise<boolean>;
  onReject: (paymentId: string) => Promise<boolean>;
}

export default function PendingPaymentConfirmations({
  participants,
  payments,
  currentUserId,
  isSaving,
  onConfirm,
  onReject,
}: PendingPaymentConfirmationsProps) {
  const participantById = new Map(participants.map((participant) => [participant.id, participant]));

  const pendingForMe = payments.filter((payment) => {
    if (payment.status !== "pending") return false;
    const recipient = participantById.get(payment.to_participant);
    return recipient?.user_id != null && recipient.user_id === currentUserId;
  });

  if (pendingForMe.length === 0) {
    return null;
  }

  return (
    <section className="panel pending-confirmations">
      <div className="panel-heading">
        <h2>Payments Awaiting Your Confirmation</h2>
      </div>
      <div className="settlement-list">
        {pendingForMe.map((payment) => {
          const payer = participantById.get(payment.from_participant);
          return (
            <div className="settlement-row" key={payment.id}>
              <span>
                <strong>{payer?.name ?? "Someone"}</strong> says they paid you{" "}
                <strong>{formatMoney(payment.currency, payment.amount)}</strong>
                {payment.note ? <span className="cell-note"> — {payment.note}</span> : null}
                <span className="cell-note"> · {payment.date}</span>
              </span>
              <div className="settlement-row-actions">
                <button
                  className="table-action-button"
                  type="button"
                  disabled={isSaving}
                  onClick={() => void onConfirm(payment.id)}
                >
                  <Check size={16} />
                  Confirm
                </button>
                <button
                  className="table-action-button danger"
                  type="button"
                  disabled={isSaving}
                  onClick={() => void onReject(payment.id)}
                >
                  <X size={16} />
                  Decline
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
