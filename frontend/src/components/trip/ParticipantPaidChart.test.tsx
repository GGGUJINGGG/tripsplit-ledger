import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ParticipantPaidChart from "./ParticipantPaidChart";

const alex = { id: "p1", name: "Alex", role: "owner" as const };
const maya = { id: "p2", name: "Maya", role: "member" as const };

describe("ParticipantPaidChart", () => {
  it("shows an empty state when nobody has paid anything", () => {
    render(
      <ParticipantPaidChart
        summary={[
          { participant: alex, paid: [] },
          { participant: maya, paid: [] },
        ]}
      />,
    );

    expect(screen.getByText("No spending yet.")).toBeInTheDocument();
  });

  it("renders a bar per participant without a legend for a single currency", () => {
    const { container } = render(
      <ParticipantPaidChart
        summary={[
          { participant: alex, paid: [{ currency: "USD", amount: 120 }] },
          { participant: maya, paid: [] },
        ]}
      />,
    );

    expect(screen.queryByText("No spending yet.")).not.toBeInTheDocument();
    expect(container.querySelectorAll(".recharts-legend-item")).toHaveLength(0);
  });

  it("renders a legend when more than one currency is present", () => {
    const { container } = render(
      <ParticipantPaidChart
        summary={[
          { participant: alex, paid: [{ currency: "USD", amount: 120 }] },
          { participant: maya, paid: [{ currency: "CNY", amount: 40 }] },
        ]}
      />,
    );

    expect(container.querySelectorAll(".recharts-legend-item")).toHaveLength(2);
  });
});
