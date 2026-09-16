import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Participant, Payment } from "../../types";
import PendingPaymentConfirmations from "./PendingPaymentConfirmations";

const participants: Participant[] = [
  { id: "p1", name: "Gujing", user_id: "user-gujing", role: "owner" },
  { id: "p2", name: "Anita", user_id: "user-anita", role: "member" },
  { id: "p3", name: "Guest Sam", role: "member" },
];

function buildPayment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: "pay-1",
    trip_id: "trip-1",
    from_participant: "p1",
    to_participant: "p2",
    amount: 40,
    currency: "USD",
    date: "2026-09-05",
    note: null,
    status: "pending",
    created_at: "2026-09-05T00:00:00Z",
    updated_at: "2026-09-05T00:00:00Z",
    ...overrides,
  };
}

function renderPanel(
  props: { payments: Payment[]; currentUserId?: string },
  onConfirm = vi.fn().mockResolvedValue(true),
  onReject = vi.fn().mockResolvedValue(true),
) {
  const result = render(
    <PendingPaymentConfirmations
      participants={participants}
      payments={props.payments}
      currentUserId={props.currentUserId}
      isSaving={false}
      onConfirm={onConfirm}
      onReject={onReject}
    />,
  );
  return { ...result, onConfirm, onReject };
}

describe("PendingPaymentConfirmations", () => {
  it("renders nothing when there is nothing pending for the current user", () => {
    const { container } = renderPanel({
      payments: [buildPayment({ status: "confirmed" })],
      currentUserId: "user-anita",
    });

    expect(container).toBeEmptyDOMElement();
  });

  it("ignores a payment pending for a different person", () => {
    // Pending for p2 (Anita), but the current user is p1 (Gujing) — the
    // payer, not the recipient, so nothing to confirm here.
    const { container } = renderPanel({
      payments: [buildPayment({ status: "pending" })],
      currentUserId: "user-gujing",
    });

    expect(container).toBeEmptyDOMElement();
  });

  it("ignores a pending payment to a participant with no account", () => {
    const { container } = renderPanel({
      payments: [
        buildPayment({ status: "pending", to_participant: "p3" }),
      ],
      currentUserId: "user-anita",
    });

    expect(container).toBeEmptyDOMElement();
  });

  it("shows a pending payment awaiting the current user's confirmation", () => {
    renderPanel({
      payments: [buildPayment({ status: "pending" })],
      currentUserId: "user-anita",
    });

    expect(screen.getByText("Gujing", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("USD 40.00", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /decline/i })).toBeInTheDocument();
  });

  it("calls onConfirm with the payment id", async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderPanel({
      payments: [buildPayment({ id: "pay-42", status: "pending" })],
      currentUserId: "user-anita",
    });

    await user.click(screen.getByRole("button", { name: /confirm/i }));

    expect(onConfirm).toHaveBeenCalledWith("pay-42");
  });

  it("calls onReject with the payment id", async () => {
    const user = userEvent.setup();
    const { onReject } = renderPanel({
      payments: [buildPayment({ id: "pay-42", status: "pending" })],
      currentUserId: "user-anita",
    });

    await user.click(screen.getByRole("button", { name: /decline/i }));

    expect(onReject).toHaveBeenCalledWith("pay-42");
  });
});
