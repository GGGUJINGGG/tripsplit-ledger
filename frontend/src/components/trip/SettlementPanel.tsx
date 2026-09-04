import { Check } from "lucide-react";
import { Link } from "react-router-dom";

import type { PaymentCreate, Settlement } from "../../types";
import { formatMoney } from "../../utils/currency";

interface SettlementPanelProps {
  tripId: string;
  settlements: Settlement[];
  isSaving: boolean;
  onRecordPayment: (payload: PaymentCreate) => Promise<boolean>;
}

export default function SettlementPanel({
  tripId,
  settlements,
  isSaving,
  onRecordPayment,
}: SettlementPanelProps) {
  const settlementsByCurrency = new Map<string, Settlement[]>();
  for (const settlement of settlements) {
    const group = settlementsByCurrency.get(settlement.currency) ?? [];
    group.push(settlement);
    settlementsByCurrency.set(settlement.currency, group);
  }
  const currencyGroups = Array.from(settlementsByCurrency.entries());

  function handleMarkPaid(settlement: Settlement) {
    void onRecordPayment({
      from_participant: settlement.from_participant_id,
      to_participant: settlement.to_participant_id,
      amount: settlement.amount,
      currency: settlement.currency,
      date: new Date().toISOString().slice(0, 10),
    });
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Settlement Summary</h2>
        <Link className="table-link" to={`/trips/${tripId}/settlements`}>
          View full page
        </Link>
      </div>
      {settlements.length === 0 ? (
        <p className="empty-state">Everyone is settled.</p>
      ) : (
        <div className="settlement-groups">
          {currencyGroups.map(([currency, group]) => (
            <div className="settlement-currency-group" key={currency}>
              {currencyGroups.length > 1 ? (
                <h3 className="settlement-currency-heading">{currency}</h3>
              ) : null}
              <div className="settlement-list">
                {group.map((settlement) => (
                  <div
                    className="settlement-row"
                    key={`${settlement.from_participant_id}-${settlement.to_participant_id}-${settlement.currency}`}
                  >
                    <span>
                      <strong>{settlement.from_name}</strong> pays{" "}
                      <strong>{settlement.to_name}</strong>
                    </span>
                    <div className="settlement-row-actions">
                      <strong>{formatMoney(settlement.currency, settlement.amount)}</strong>
                      <button
                        className="table-action-button"
                        type="button"
                        disabled={isSaving}
                        onClick={() => handleMarkPaid(settlement)}
                        title="Record this as paid today"
                      >
                        <Check size={16} />
                        Mark as paid
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
