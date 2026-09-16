import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Participant, Payment, Settlement } from "../../types";
import PaymentsPanel from "./PaymentsPanel";

const participants: Participant[] = [
  { id: "p1", name: "Gujing", role: "owner" },
  { id: "p2", name: "Anita", role: "member" },
];

const participantNames = new Map(
  participants.map((participant) => [participant.id, participant.name]),
);

function renderPanel({
  payments = [] as Payment[],
  settlements = [] as Settlement[],
  onRecordPayment = vi.fn().mockResolvedValue(true),
  onRemovePayment = vi.fn().mockResolvedValue(true),
} = {}) {
  render(
    <PaymentsPanel
      participants={participants}
      payments={payments}
      participantNames={participantNames}
      settlements={settlements}
      isSaving={false}
      onRecordPayment={onRecordPayment}
      onRemovePayment={onRemovePayment}
    />,
  );
  return { onRecordPayment, onRemovePayment };
}

describe("PaymentsPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

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
    const { onRecordPayment } = renderPanel({
      settlements: [
        {
          from_participant_id: "p2",
          from_name: "Anita",
          to_participant_id: "p1",
          to_name: "Gujing",
          amount: 45,
          currency: "USD",
        },
      ],
    });

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

  it("caps the date field's max at today", () => {
    renderPanel();

    const today = new Date().toISOString().slice(0, 10);
    expect(screen.getByLabelText("Date")).toHaveAttribute("max", today);
  });

  it("marks a future date as invalid via the input's max constraint", () => {
    renderPanel();

    const dateInput = screen.getByLabelText("Date") as HTMLInputElement;
    fireEvent.change(dateInput, { target: { value: "2099-01-01" } });

    expect(dateInput.validity.valid).toBe(false);
    expect(dateInput.validity.rangeOverflow).toBe(true);
  });

  it("shows an error and does not submit when a future date slips past the native constraint", async () => {
    // Belt-and-suspenders check in handleSubmit itself, in case the date
    // ever reaches it some other way than typing into the input (e.g. a
    // browser without max-date support) — bypass the input entirely and
    // drive React's state straight from an out-of-range value.
    const user = userEvent.setup();
    const { onRecordPayment } = renderPanel();

    await user.selectOptions(screen.getByLabelText("Paid by"), "p1");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p2");
    await user.type(screen.getByLabelText("Amount"), "30");
    const dateInput = screen.getByLabelText("Date") as HTMLInputElement;
    dateInput.removeAttribute("max");
    fireEvent.change(dateInput, { target: { value: "2099-01-01" } });
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(screen.getByText(/date can't be in the future/i)).toBeInTheDocument();
    expect(onRecordPayment).not.toHaveBeenCalled();
  });

  it("submits without confirming when the amount is within what the recipient is owed", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm");
    const { onRecordPayment } = renderPanel({
      settlements: [
        {
          from_participant_id: "p2",
          from_name: "Anita",
          to_participant_id: "p1",
          to_name: "Gujing",
          amount: 40,
          currency: "USD",
        },
      ],
    });

    await user.selectOptions(screen.getByLabelText("Paid by"), "p2");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p1");
    await user.type(screen.getByLabelText("Amount"), "30");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(onRecordPayment).toHaveBeenCalledTimes(1);
  });

  it("sums what's owed to the recipient across every debtor, not just the selected payer", async () => {
    // Gujing covers Sam's share too: Anita is owed 20 from Sam and 20
    // from Gujing (40 total), so Gujing paying the full 40 shouldn't
    // trigger a confirmation even though Gujing alone only owes 20.
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm");
    const { onRecordPayment } = renderPanel({
      settlements: [
        {
          from_participant_id: "sam",
          from_name: "Sam",
          to_participant_id: "p2",
          to_name: "Anita",
          amount: 20,
          currency: "USD",
        },
        {
          from_participant_id: "p1",
          from_name: "Gujing",
          to_participant_id: "p2",
          to_name: "Anita",
          amount: 20,
          currency: "USD",
        },
      ],
    });

    await user.selectOptions(screen.getByLabelText("Paid by"), "p1");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p2");
    await user.type(screen.getByLabelText("Amount"), "40");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(onRecordPayment).toHaveBeenCalledTimes(1);
  });

  it("asks for confirmation when the amount exceeds what the recipient is owed, and submits if confirmed", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const { onRecordPayment } = renderPanel({
      settlements: [
        {
          from_participant_id: "p2",
          from_name: "Anita",
          to_participant_id: "p1",
          to_name: "Gujing",
          amount: 40,
          currency: "USD",
        },
      ],
    });

    await user.selectOptions(screen.getByLabelText("Paid by"), "p2");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p1");
    await user.type(screen.getByLabelText("Amount"), "100");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(confirmSpy.mock.calls[0][0]).toMatch(/only owed USD 40\.00/);
    expect(onRecordPayment).toHaveBeenCalledTimes(1);
  });

  it("does not submit when the overage confirmation is declined", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const { onRecordPayment } = renderPanel({
      settlements: [
        {
          from_participant_id: "p2",
          from_name: "Anita",
          to_participant_id: "p1",
          to_name: "Gujing",
          amount: 40,
          currency: "USD",
        },
      ],
    });

    await user.selectOptions(screen.getByLabelText("Paid by"), "p2");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p1");
    await user.type(screen.getByLabelText("Amount"), "100");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(onRecordPayment).not.toHaveBeenCalled();
  });

  it("asks for confirmation when the recipient isn't owed anything at all in that currency", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const { onRecordPayment } = renderPanel({ settlements: [] });

    await user.selectOptions(screen.getByLabelText("Paid by"), "p2");
    await user.selectOptions(screen.getByLabelText("Paid to"), "p1");
    await user.type(screen.getByLabelText("Amount"), "10");
    await user.click(screen.getByRole("button", { name: /record payment/i }));

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(onRecordPayment).toHaveBeenCalledTimes(1);
  });

  it("renders payment history with resolved names and formatted amounts", () => {
    renderPanel({
      payments: [
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
      ],
    });

    expect(screen.getByText("Anita", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("Gujing", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("CNY 20.00")).toBeInTheDocument();
    expect(screen.getByText(/Parking split/)).toBeInTheDocument();
  });

  it("calls onRemovePayment with the payment id when undo is clicked", async () => {
    const user = userEvent.setup();
    const { onRemovePayment } = renderPanel({
      payments: [
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
      ],
    });

    await user.click(screen.getByRole("button", { name: /undo this payment/i }));

    expect(onRemovePayment).toHaveBeenCalledWith("pay-1");
  });
});
