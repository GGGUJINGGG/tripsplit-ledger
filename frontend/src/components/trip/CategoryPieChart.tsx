import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { ExpenseCategory } from "../../types";
import { formatMoney } from "../../utils/currency";

interface CategorySummaryItem {
  category: ExpenseCategory;
  currency: string;
  total: number;
}

interface CategoryPieChartProps {
  categorySummary: CategorySummaryItem[];
}

const SLICE_COLORS = [
  "#2563a8",
  "#c2703d",
  "#3d8a5f",
  "#8a4fae",
  "#b8455c",
  "#4a8fa8",
  "#a8942f",
];

export default function CategoryPieChart({ categorySummary }: CategoryPieChartProps) {
  const currencies = Array.from(new Set(categorySummary.map((item) => item.currency))).sort();

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Category Breakdown</h2>
      </div>
      {categorySummary.length === 0 ? (
        <p className="empty-state">No category spending yet.</p>
      ) : (
        <div className="chart-groups">
          {currencies.map((currency) => {
            const slices = categorySummary.filter((item) => item.currency === currency);
            return (
              <div className="chart-currency-group" key={currency}>
                {currencies.length > 1 ? (
                  <h3 className="settlement-currency-heading">{currency}</h3>
                ) : null}
                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie
                        data={slices}
                        dataKey="total"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={85}
                        paddingAngle={2}
                        isAnimationActive={false}
                      >
                        {slices.map((slice, index) => (
                          <Cell
                            key={slice.category}
                            fill={SLICE_COLORS[index % SLICE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatMoney(currency, Number(value))} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
