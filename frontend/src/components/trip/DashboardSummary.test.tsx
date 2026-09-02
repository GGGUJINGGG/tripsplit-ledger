import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Trip } from "../../types";
import DashboardSummary from "./DashboardSummary";

const trip: Trip = {
  id: "trip-1",
  name: "Iceland Road Trip",
  start_date: "2026-07-01",
  end_date: null,
  participants: [
    { id: "p1", name: "Alex" },
    { id: "p2", name: "Maya" },
  ],
  expenses: [
    {
      id: "e1",
      trip_id: "trip-1",
      title: "Hotel",
      amount: 300,
      paid_by: "p1",
      split_among: ["p1", "p2"],
      expense_type: "shared",
      category: "hotel",
      date: "2026-07-01",
      currency: "USD",
      note: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    },
  ],
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

describe("DashboardSummary", () => {
  it("renders spending totals and counts", () => {
    render(
      <DashboardSummary
        trip={trip}
        spendingByCurrency={[{ currency: "USD", amount: 300 }]}
        sharedSpendingByCurrency={[{ currency: "USD", amount: 300 }]}
        personalSpendingByCurrency={[]}
      />,
    );

    expect(screen.getByText("Total spending")).toBeInTheDocument();
    expect(screen.getAllByText("USD 300.00")).toHaveLength(2);
    expect(screen.getByText("Participants").nextSibling).toHaveTextContent("2");
    expect(screen.getByText("Expenses").nextSibling).toHaveTextContent("1");
  });

  it("falls back to USD 0.00 for currencies with no spending", () => {
    render(
      <DashboardSummary
        trip={trip}
        spendingByCurrency={[{ currency: "USD", amount: 300 }]}
        sharedSpendingByCurrency={[{ currency: "USD", amount: 300 }]}
        personalSpendingByCurrency={[]}
      />,
    );

    const personalCard = screen.getByText("Personal spending").closest(".metric-card");
    expect(personalCard).toHaveTextContent("USD 0.00");
  });

  it("renders one line per currency for multi-currency trips", () => {
    render(
      <DashboardSummary
        trip={trip}
        spendingByCurrency={[
          { currency: "USD", amount: 300 },
          { currency: "EUR", amount: 50 },
        ]}
        sharedSpendingByCurrency={[]}
        personalSpendingByCurrency={[]}
      />,
    );

    const totalCard = screen.getByText("Total spending").closest(".metric-card");
    expect(totalCard).toHaveTextContent("USD 300.00");
    expect(totalCard).toHaveTextContent("EUR 50.00");
  });
});
