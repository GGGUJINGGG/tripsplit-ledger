import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatMoney } from "../../utils/currency";

interface DailySpendingItem {
  date: string;
  currency: string;
  amount: number;
}

interface SpendingTrendChartProps {
  dailySpendingByCurrency: DailySpendingItem[];
}

const LINE_COLORS = ["#2563a8", "#c2703d", "#3d8a5f", "#8a4fae"];

export default function SpendingTrendChart({
  dailySpendingByCurrency,
}: SpendingTrendChartProps) {
  const currencies = Array.from(
    new Set(dailySpendingByCurrency.map((item) => item.currency)),
  ).sort();

  const rowsByDate = new Map<string, Record<string, number | string>>();
  for (const item of dailySpendingByCurrency) {
    const row = rowsByDate.get(item.date) ?? { date: item.date };
    row[item.currency] = item.amount;
    rowsByDate.set(item.date, row);
  }
  const data = Array.from(rowsByDate.values()).sort((first, second) =>
    String(first.date).localeCompare(String(second.date)),
  );

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Spending Over Time</h2>
      </div>
      {data.length === 0 ? (
        <p className="empty-state">No spending yet.</p>
      ) : (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5eaf0" />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#687381" }} />
              <YAxis tick={{ fontSize: 12, fill: "#687381" }} />
              <Tooltip
                formatter={(value, name) => formatMoney(String(name), Number(value))}
                labelStyle={{ color: "#1e242b" }}
              />
              {currencies.length > 1 ? <Legend /> : null}
              {currencies.map((currency, index) => (
                <Line
                  key={currency}
                  type="monotone"
                  dataKey={currency}
                  name={currency}
                  stroke={LINE_COLORS[index % LINE_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  connectNulls
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
