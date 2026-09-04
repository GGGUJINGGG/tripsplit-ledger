import { Link } from "react-router-dom";

import type { Settlement } from "../../types";
import { type CurrencyCode, formatMoney } from "../../utils/currency";

interface SettlementPanelProps {
  tripId: string;
  settlements: Settlement[];
  settlementCurrency: CurrencyCode | null;
}

export default function SettlementPanel({
  tripId,
  settlements,
  settlementCurrency,
}: SettlementPanelProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Settlement Summary</h2>
        <Link className="table-link" to={`/trips/${tripId}/settlements`}>
          View full page
        </Link>
      </div>
      {settlementCurrency === null ? (
        <p className="empty-state">
          Settlements are hidden for mixed-currency trips until exchange-rate
          conversion is supported.
        </p>
      ) : settlements.length === 0 ? (
        <p className="empty-state">Everyone is settled.</p>
      ) : (
        <div className="settlement-list">
          {settlements.map((settlement) => (
            <div
              className="settlement-row"
              key={`${settlement.from_participant_id}-${settlement.to_participant_id}`}
            >
              <span>
                <strong>{settlement.from_name}</strong> pays{" "}
                <strong>{settlement.to_name}</strong>
              </span>
              <strong>{formatMoney(settlementCurrency, settlement.amount)}</strong>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
