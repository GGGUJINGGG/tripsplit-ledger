import type { Trip } from "../../types";
import { type CurrencyCode, formatMoney } from "../../utils/currency";

interface MoneyByCurrency {
  currency: CurrencyCode;
  amount: number;
}

interface DashboardSummaryProps {
  trip: Trip;
  spendingByCurrency: MoneyByCurrency[];
  sharedSpendingByCurrency: MoneyByCurrency[];
  personalSpendingByCurrency: MoneyByCurrency[];
}

function MetricCard({ label, items }: { label: string; items: MoneyByCurrency[] }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      {items.length === 0 ? (
        <strong>USD 0.00</strong>
      ) : (
        <div className="metric-list">
          {items.map((item) => (
            <strong key={item.currency}>{formatMoney(item.currency, item.amount)}</strong>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashboardSummary({
  trip,
  spendingByCurrency,
  sharedSpendingByCurrency,
  personalSpendingByCurrency,
}: DashboardSummaryProps) {
  return (
    <div className="summary-row">
      <MetricCard label="Total spending" items={spendingByCurrency} />
      <MetricCard label="Shared spending" items={sharedSpendingByCurrency} />
      <MetricCard label="Personal spending" items={personalSpendingByCurrency} />
      <div className="metric-card">
        <span>Participants</span>
        <strong>{trip.participants.length}</strong>
      </div>
      <div className="metric-card">
        <span>Expenses</span>
        <strong>{trip.expenses.length}</strong>
      </div>
    </div>
  );
}
