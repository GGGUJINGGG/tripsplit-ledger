import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SpendingTrendChart from "./SpendingTrendChart";

describe("SpendingTrendChart", () => {
  it("shows an empty state when there is no spending", () => {
    render(<SpendingTrendChart dailySpendingByCurrency={[]} />);

    expect(screen.getByText("No spending yet.")).toBeInTheDocument();
  });

  it("renders a chart when there is spending data", () => {
    const { container } = render(
      <SpendingTrendChart
        dailySpendingByCurrency={[
          { date: "2026-07-01", currency: "USD", amount: 100 },
          { date: "2026-07-02", currency: "USD", amount: 40 },
        ]}
      />,
    );

    expect(screen.queryByText("No spending yet.")).not.toBeInTheDocument();
    expect(container.querySelector(".chart-wrap")).toBeInTheDocument();
  });

  it("renders a legend when more than one currency is present", () => {
    const { container } = render(
      <SpendingTrendChart
        dailySpendingByCurrency={[
          { date: "2026-07-01", currency: "USD", amount: 100 },
          { date: "2026-07-02", currency: "CNY", amount: 40 },
        ]}
      />,
    );

    expect(container.querySelectorAll(".recharts-legend-item")).toHaveLength(2);
  });

  it("does not render a legend for a single currency", () => {
    const { container } = render(
      <SpendingTrendChart
        dailySpendingByCurrency={[{ date: "2026-07-01", currency: "USD", amount: 100 }]}
      />,
    );

    expect(container.querySelectorAll(".recharts-legend-item")).toHaveLength(0);
  });
});
