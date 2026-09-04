import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { Settlement } from "../../types";
import SettlementPanel from "./SettlementPanel";

function renderPanel(settlements: Settlement[]) {
  return render(
    <MemoryRouter>
      <SettlementPanel tripId="trip-1" settlements={settlements} />
    </MemoryRouter>,
  );
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
});
