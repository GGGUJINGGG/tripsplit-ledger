import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ParticipantSummary from "./ParticipantSummary";

describe("ParticipantSummary", () => {
  it("renders shared responsibility and net balance from the given amounts", () => {
    render(
      <ParticipantSummary
        summary={[
          {
            participant: { id: "p1", name: "Alex", role: "owner" },
            paid: [{ currency: "USD", amount: 100 }],
            sharedResponsibility: [{ currency: "USD", amount: 40 }],
            personal: [],
            netBalances: [{ currency: "USD", amount: 60 }],
          },
        ]}
        settlementCurrency="USD"
      />,
    );

    const row = screen.getByText("Alex").closest("tr");
    expect(row).toHaveTextContent("USD 100.00");
    expect(row).toHaveTextContent("USD 40.00");
    expect(row).toHaveTextContent("+USD 60.00");
  });

  it("shows 'Mixed currencies' for shared responsibility and net balance when the trip has more than one currency", () => {
    render(
      <ParticipantSummary
        summary={[
          {
            participant: { id: "p1", name: "Alex", role: "owner" },
            paid: [
              { currency: "USD", amount: 100 },
              { currency: "EUR", amount: 20 },
            ],
            // Backend numbers aren't currency-safe once a trip mixes
            // currencies, so the hook doesn't attempt to attribute them.
            sharedResponsibility: [],
            personal: [],
            netBalances: [],
          },
        ]}
        settlementCurrency={null}
      />,
    );

    const row = screen.getByText("Alex").closest("tr");
    const cells = row!.querySelectorAll("td");
    expect(cells[2]).toHaveTextContent("Mixed currencies");
    expect(cells[4]).toHaveTextContent("Mixed currencies");
  });

  it("shows an empty state when there are no participants", () => {
    render(<ParticipantSummary summary={[]} settlementCurrency="USD" />);

    expect(
      screen.getByText("Add participants to see spending summaries."),
    ).toBeInTheDocument();
  });
});
