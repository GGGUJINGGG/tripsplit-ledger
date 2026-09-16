import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { Participant, Settlement } from "../../types";
import SettlementPanel from "./SettlementPanel";

function renderPanel(
  settlements: Settlement[],
  participants: Participant[] = [],
  currentUserId?: string,
  onRecordPayment = vi.fn().mockResolvedValue(true),
) {
  render(
    <MemoryRouter>
      <SettlementPanel
        tripId="trip-1"
        participants={participants}
        settlements={settlements}
        currentUserId={currentUserId}
        isSaving={false}
        onRecordPayment={onRecordPayment}
      />
    </MemoryRouter>,
  );
  return { onRecordPayment };
}

describe("SettlementPanel", () => {
  it("shows 'Everyone is settled' when there are no settlements", () => {
    renderPanel([]);

    expect(screen.getByText("Everyone is settled.")).toBeInTheDocument();
  });

  it("renders a single currency's settlements without a currency heading", () => {
    renderPanel([
      {
        from_participant_id: "p1",
        from_name: "Gujing",
        to_participant_id: "p2",
        to_name: "Anita",
        amount: 60,
        currency: "USD",
      },
    ]);

    expect(screen.getByText("Gujing")).toBeInTheDocument();
    expect(screen.getByText("USD 60.00")).toBeInTheDocument();
    expect(screen.queryByText("USD", { selector: "h3" })).not.toBeInTheDocument();
  });

  it("groups mixed-currency settlements under a heading per currency", () => {
    renderPanel([
      {
        from_participant_id: "p1",
        from_name: "Gujing",
        to_participant_id: "p2",
        to_name: "Anita",
        amount: 60,
        currency: "USD",
      },
      {
        from_participant_id: "p2",
        from_name: "Anita",
        to_participant_id: "p1",
        to_name: "Gujing",
        amount: 20,
        currency: "CNY",
      },
    ]);

    expect(screen.getByRole("heading", { level: 3, name: "USD" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "CNY" })).toBeInTheDocument();
    expect(screen.getByText("USD 60.00")).toBeInTheDocument();
    expect(screen.getByText("CNY 20.00")).toBeInTheDocument();
  });

  it("records a matching payment when 'Mark as paid' is clicked", async () => {
    const { onRecordPayment } = renderPanel([
      {
        from_participant_id: "p1",
        from_name: "Gujing",
        to_participant_id: "p2",
        to_name: "Anita",
        amount: 60,
        currency: "USD",
      },
    ]);

    await userEvent.click(screen.getByRole("button", { name: /mark as paid/i }));

    expect(onRecordPayment).toHaveBeenCalledTimes(1);
    const payload = onRecordPayment.mock.calls[0][0];
    expect(payload).toMatchObject({
      from_participant: "p1",
      to_participant: "p2",
      amount: 60,
      currency: "USD",
    });
    expect(payload.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("shows 'Mark as paid' when the debtor has no account (anyone can record for them)", () => {
    renderPanel(
      [
        {
          from_participant_id: "p1",
          from_name: "Guest Sam",
          to_participant_id: "p2",
          to_name: "Anita",
          amount: 60,
          currency: "USD",
        },
      ],
      [
        { id: "p1", name: "Guest Sam", role: "member" },
        { id: "p2", name: "Anita", user_id: "user-anita", role: "owner" },
      ],
      "user-anita",
    );

    expect(screen.getByRole("button", { name: /mark as paid/i })).toBeInTheDocument();
  });

  it("shows 'Mark as paid' when the current user is the debtor", () => {
    renderPanel(
      [
        {
          from_participant_id: "p1",
          from_name: "Gujing",
          to_participant_id: "p2",
          to_name: "Anita",
          amount: 60,
          currency: "USD",
        },
      ],
      [
        { id: "p1", name: "Gujing", user_id: "user-gujing", role: "owner" },
        { id: "p2", name: "Anita", user_id: "user-anita", role: "member" },
      ],
      "user-gujing",
    );

    expect(screen.getByRole("button", { name: /mark as paid/i })).toBeInTheDocument();
  });

  it("hides 'Mark as paid' and explains why when the debtor is a different registered member", () => {
    renderPanel(
      [
        {
          from_participant_id: "p1",
          from_name: "Gujing",
          to_participant_id: "p2",
          to_name: "Anita",
          amount: 60,
          currency: "USD",
        },
      ],
      [
        { id: "p1", name: "Gujing", user_id: "user-gujing", role: "member" },
        { id: "p2", name: "Anita", user_id: "user-anita", role: "owner" },
      ],
      "user-anita",
    );

    expect(screen.queryByRole("button", { name: /mark as paid/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Only Gujing can mark this as paid/)).toBeInTheDocument();
  });
});
