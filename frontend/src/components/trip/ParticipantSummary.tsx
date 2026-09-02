import type { Participant } from "../../types";
import { type CurrencyCode, formatMoneyItems, formatSignedMoney } from "../../utils/currency";

interface MoneyByCurrency {
  currency: CurrencyCode;
  amount: number;
}

interface ParticipantSpending {
  participant: Participant;
  paid: MoneyByCurrency[];
  sharedResponsibility: MoneyByCurrency[];
  personal: MoneyByCurrency[];
  netBalances: MoneyByCurrency[];
}

interface ParticipantSummaryProps {
  summary: ParticipantSpending[];
  settlementCurrency: CurrencyCode | null;
}

export default function ParticipantSummary({
  summary,
  settlementCurrency,
}: ParticipantSummaryProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Participant Spending</h2>
        <span className="muted">{summary.length} people</span>
      </div>
      {summary.length === 0 ? (
        <p className="empty-state">Add participants to see spending summaries.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Participant</th>
                <th>Total Paid</th>
                <th>Shared Responsibility</th>
                <th>Personal Spending</th>
                <th>Net Balance</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((item) => (
                <tr key={item.participant.id}>
                  <td>
                    <strong>{item.participant.name}</strong>
                  </td>
                  <td>{formatMoneyItems(item.paid)}</td>
                  <td>
                    {settlementCurrency === null
                      ? "Mixed currencies"
                      : formatMoneyItems(item.sharedResponsibility)}
                  </td>
                  <td>{formatMoneyItems(item.personal)}</td>
                  <td>
                    {settlementCurrency === null
                      ? "Mixed currencies"
                      : item.netBalances.length === 0
                        ? "USD 0.00"
                        : item.netBalances
                            .map((balance) =>
                              formatSignedMoney(balance.currency, balance.amount),
                            )
                            .join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
