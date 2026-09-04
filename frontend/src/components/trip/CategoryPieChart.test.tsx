import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CategoryPieChart from "./CategoryPieChart";

describe("CategoryPieChart", () => {
  it("shows an empty state when there is no category spending", () => {
    render(<CategoryPieChart categorySummary={[]} />);

    expect(screen.getByText("No category spending yet.")).toBeInTheDocument();
  });

  it("renders one pie without a currency heading for a single currency", () => {
    const { container } = render(
      <CategoryPieChart
        categorySummary={[
          { category: "hotel", currency: "USD", total: 100 },
          { category: "food", currency: "USD", total: 50 },
        ]}
      />,
    );

    expect(container.querySelectorAll(".chart-currency-group")).toHaveLength(1);
    expect(screen.queryByText("USD")).not.toBeInTheDocument();
  });

  it("renders one pie per currency with headings when mixed", () => {
    const { container } = render(
      <CategoryPieChart
        categorySummary={[
          { category: "hotel", currency: "USD", total: 100 },
          { category: "transportation", currency: "CNY", total: 40 },
        ]}
      />,
    );

    expect(container.querySelectorAll(".chart-currency-group")).toHaveLength(2);
    expect(screen.getByText("USD")).toBeInTheDocument();
    expect(screen.getByText("CNY")).toBeInTheDocument();
  });
});
