import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Participant } from "../../types";
import { formatMoney } from "../../utils/currency";

interface MoneyByCurrency {
  currency: string;
  amount: number;
}

interface ParticipantPaidChartProps {
  summary: Array<{ participant: Participant; paid: MoneyByCurrency[] }>;
}

const BAR_COLORS = ["#2563a8", "#c2703d", "#3d8a5f", "#8a4fae"];

export default function ParticipantPaidChart({ summary }: ParticipantPaidChartProps) {
  const currencies = Array.from(
    new Set(summary.flatMap((item) => item.paid.map((money) => money.currency))),
  ).sort();

  const data = summary.map((item) => {
    const row: Record<string, number | string> = { name: item.participant.name };
    for (const money of item.paid) {
      row[money.currency] = money.amount;
    }
    return row;
  });

  const hasData = data.some((row) =>
    currencies.some((currency) => typeof row[currency] === "number"),
  );

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Who Paid</h2>
      </div>
      {!hasData ? (
        <p className="empty-state">No spending yet.</p>
      ) : (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5eaf0" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#687381" }} />
              <YAxis tick={{ fontSize: 12, fill: "#687381" }} />
              <Tooltip
                formatter={(value, name) => formatMoney(String(name), Number(value))}
                labelStyle={{ color: "#1e242b" }}
              />
              {currencies.length > 1 ? <Legend /> : null}
              {currencies.map((currency, index) => (
                <Bar
                  key={currency}
                  dataKey={currency}
                  name={currency}
                  fill={BAR_COLORS[index % BAR_COLORS.length]}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
