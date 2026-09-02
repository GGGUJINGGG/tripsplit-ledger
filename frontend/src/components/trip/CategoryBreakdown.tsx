import type { ExpenseCategory } from "../../types";
import { type CurrencyCode, formatMoney } from "../../utils/currency";

interface CategorySummaryItem {
  category: ExpenseCategory;
  currency: CurrencyCode;
  shared: number;
  personal: number;
  total: number;
}

interface CategoryBreakdownProps {
  categorySummary: CategorySummaryItem[];
}

export default function CategoryBreakdown({ categorySummary }: CategoryBreakdownProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Category Summary</h2>
        <span className="muted">{categorySummary.length} categories</span>
      </div>
      {categorySummary.length === 0 ? (
        <p className="empty-state">No category spending yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Shared</th>
                <th>Personal</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {categorySummary.map((item) => (
                <tr key={`${item.category}-${item.currency}`}>
                  <td>{item.category}</td>
                  <td>{formatMoney(item.currency, item.shared)}</td>
                  <td>{formatMoney(item.currency, item.personal)}</td>
                  <td>{formatMoney(item.currency, item.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
