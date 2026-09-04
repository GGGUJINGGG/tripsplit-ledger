import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Participant, Payment } from "../../types";
import PaymentsPanel from "./PaymentsPanel";

const participants: Participant[] = [
  { id: "p1", name: "Gujing", role: "owner" },
  { id: "p2", name: "Anita", role: "member" },
];

const participantNames = new Map(
  participants.map((participant) => [participant.id, participant.name]),
);

function renderPanel(
  payments: Payment[] = [],
  onRecordPayment = vi.fn().mockResolvedValue(true),
  onRemovePayment = vi.fn().mockResolvedValue(true),
) {
  render(
    <PaymentsPanel
      participants={participants}
      payments={payments}
      participantNames={participantNames}
      isSaving={false}
      onRecordPayment={onRecordPayment}
      onRemovePayment={onRemovePayment}
    />,
  );
  return { onRecordPayment, onRemovePayment };
}

describe("PaymentsPanel", () => {
  it("shows an error and does not submit when payer and recipient are the same", async () => {
    const user = userEvent.setup();
    const { onRecordPayment } = renderPanel();

    await user.selectOptions(screen.getByLabelText("Paid by"), "p1");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p1");
    await user.type(screen.getByLabelText("Amount"), "30");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(screen.getByText(/must be two different people/i)).toBeInTheDocument();
    expect(onRecordPayment).not.toHaveBeenCalled();
  });

  it("shows an error when the amount is not greater than 0", async () => {
    const user = userEvent.setup();
    const { onRecordPayment } = renderPanel();

    await user.selectOptions(screen.getByLabelText("Paid by"), "p1");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p2");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(screen.getByText(/amount must be greater than 0/i)).toBeInTheDocument();
    expect(onRecordPayment).not.toHaveBeenCalled();
  });

  it("submits a valid payment and resets the form", async () => {
    const user = userEvent.setup();
    const { onRecordPayment } = renderPanel();

    await user.selectOptions(screen.getByLabelText("Paid by"), "p2");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p1");
    await user.type(screen.getByLabelText("Amount"), "45");
    await user.type(screen.getByLabelText("Note"), "Cash back");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(onRecordPayment).toHaveBeenCalledTimes(1);
    const payload = onRecordPayment.mock.calls[0][0];
    expect(payload).toMatchObject({
      from_participant: "p2",
      to_participant: "p1",
      amount: 45,
      currency: "USD",
      note: "Cash back",
    });

    expect(await screen.findByLabelText("Amount")).toHaveValue(null);
  });

  it("renders payment history with resolved names and formatted amounts", () => {
    renderPanel([
      {
        id: "pay-1",
        trip_id: "trip-1",
        from_participant: "p2",
        to_participant: "p1",
        amount: 20,
        currency: "CNY",
        date: "2026-09-05",
        note: "Parking split",
        created_at: "2026-09-05T00:00:00Z",
        updated_at: "2026-09-05T00:00:00Z",
      },
    ]);

    expect(screen.getByText("Anita", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("Gujing", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("CNY 20.00")).toBeInTheDocument();
    expect(screen.getByText(/Parking split/)).toBeInTheDocument();
  });

  it("calls onRemovePayment with the payment id when undo is clicked", async () => {
    const user = userEvent.setup();
    const { onRemovePayment } = renderPanel([
      {
        id: "pay-1",
        trip_id: "trip-1",
        from_participant: "p2",
        to_participant: "p1",
        amount: 20,
        currency: "USD",
        date: "2026-09-05",
        note: null,
        created_at: "2026-09-05T00:00:00Z",
        updated_at: "2026-09-05T00:00:00Z",
      },
    ]);

    await user.click(screen.getByRole("button", { name: /undo this payment/i }));

    expect(onRemovePayment).toHaveBeenCalledWith("pay-1");
  });
});
