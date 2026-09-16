import { FormEvent, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import type { Participant, Payment, PaymentCreate, Settlement } from "../../types";
import { type CurrencyCode, currencies, formatMoney } from "../../utils/currency";

interface PaymentsPanelProps {
  participants: Participant[];
  payments: Payment[];
  participantNames: Map<string, string>;
  settlements: Settlement[];
  currentUserId?: string;
  isSaving: boolean;
  onRecordPayment: (payload: PaymentCreate) => Promise<boolean>;
  onRemovePayment: (paymentId: string) => Promise<boolean>;
}

export default function PaymentsPanel({
  participants,
  payments,
  participantNames,
  settlements,
  currentUserId,
  isSaving,
  onRecordPayment,
  onRemovePayment,
}: PaymentsPanelProps) {
  const [fromParticipant, setFromParticipant] = useState("");
  const [toParticipant, setToParticipant] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  function resetFields() {
    setFromParticipant("");
    setToParticipant("");
    setAmount("");
    setCurrency("USD");
    setDate("");
    setNote("");
    setFormError(null);
  }

  const today = new Date().toISOString().slice(0, 10);

  // A registered member can only be claimed as the payer by themselves —
  // a placeholder (no account) member has nobody who could object, so
  // anyone can still record a payment on their behalf.
  const eligiblePayers = participants.filter(
    (participant) => participant.user_id == null || participant.user_id === currentUserId,
  );

  // How much this person is currently owed in total, in this currency —
  // not just from the one payer selected below, so covering someone
  // else's share in the same payment (e.g. paying a friend's portion
  // too) is never mistaken for an oversized/mistyped amount.
  function totalOwedTo(participantId: string, forCurrency: CurrencyCode): number {
    return settlements
      .filter(
        (settlement) =>
          settlement.to_participant_id === participantId &&
          settlement.currency === forCurrency,
      )
      .reduce((sum, settlement) => sum + settlement.amount, 0);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const parsedAmount = Number(amount);
    if (!fromParticipant || !toParticipant) {
      setFormError("Choose who paid and who received it.");
      return;
    }
    if (fromParticipant === toParticipant) {
      setFormError("These must be two different people.");
      return;
    }
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setFormError("Amount must be greater than 0.");
      return;
    }
    if (date && date > today) {
      setFormError("Date can't be in the future.");
      return;
    }

    const owed = totalOwedTo(toParticipant, currency);
    if (parsedAmount > owed) {
      const recipientName = participantNames.get(toParticipant) ?? "this person";
      const confirmed = window.confirm(
        `${recipientName} is currently only owed ${formatMoney(currency, owed)}. ` +
          `Record this ${formatMoney(currency, parsedAmount)} payment anyway?`,
      );
      if (!confirmed) {
        return;
      }
    }

    setFormError(null);
    const succeeded = await onRecordPayment({
      from_participant: fromParticipant,
      to_participant: toParticipant,
      amount: parsedAmount,
      currency,
      date: date || today,
      note: note.trim() || undefined,
    });

    if (succeeded) {
      resetFields();
    }
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Record a Payment</h2>
      </div>
      {formError ? <div className="alert">{formError}</div> : null}
      <p className="field-hint">
        A registered member can only be recorded as having paid by themselves — a
        member with no account can be recorded by anyone, since they can't log in
        to do it themselves.
      </p>
      <form className="form-grid compact" onSubmit={handleSubmit}>
        <label htmlFor="payment-from">
          Paid by
          <select
            id="payment-from"
            value={fromParticipant}
            onChange={(event) => setFromParticipant(event.target.value)}
          >
            <option value="">Select person</option>
            {eligiblePayers.map((participant) => (
              <option key={participant.id} value={participant.id}>
                {participant.name}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="payment-to">
          Paid to
          <select
            id="payment-to"
            value={toParticipant}
            onChange={(event) => setToParticipant(event.target.value)}
          >
            <option value="">Select person</option>
            {participants.map((participant) => (
              <option key={participant.id} value={participant.id}>
                {participant.name}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="payment-amount">
          Amount
          <input
            id="payment-amount"
            type="number"
            min="0"
            step="0.01"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="50.00"
          />
        </label>
        <label htmlFor="payment-currency">
          Currency
          <select
            id="payment-currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value as CurrencyCode)}
          >
            {currencies.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="payment-date">
          Date
          <input
            id="payment-date"
            type="date"
            value={date}
            max={today}
            onChange={(event) => setDate(event.target.value)}
          />
        </label>
        <label className="wide-field" htmlFor="payment-note">
          Note
          <input
            id="payment-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <div className="form-actions wide-field">
          <button className="primary-button" type="submit" disabled={isSaving}>
            <Plus size={18} />
            Record payment
          </button>
        </div>
      </form>

      {payments.length > 0 ? (
        <div className="settlement-list payment-history">
          {payments.map((payment) => {
            const recipientName = participantNames.get(payment.to_participant) ?? "Unknown";
            const statusNote =
              payment.status === "pending"
                ? `Pending ${recipientName}'s confirmation`
                : payment.status === "rejected"
                  ? `Declined by ${recipientName}`
                  : null;

            return (
              <div className="settlement-row" key={payment.id}>
                <span>
                  <strong>{participantNames.get(payment.from_participant) ?? "Unknown"}</strong>{" "}
                  paid <strong>{recipientName}</strong>
                  {payment.note ? <span className="cell-note"> — {payment.note}</span> : null}
                  <span className="cell-note"> · {payment.date}</span>
                  {statusNote ? <span className="cell-note"> · {statusNote}</span> : null}
                </span>
                <div className="settlement-row-actions">
                  <strong>{formatMoney(payment.currency, payment.amount)}</strong>
                  <button
                    className="table-action-button danger"
                    type="button"
                    disabled={isSaving}
                    onClick={() => void onRemovePayment(payment.id)}
                    aria-label="Undo this payment"
                    title="Undo this payment"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
