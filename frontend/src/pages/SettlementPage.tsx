import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getSettlements } from "../api/settlements";
import { getTrip } from "../api/trips";
import type { Settlement, Trip } from "../types";

function expenseCurrencyCodes(trip: Trip | null): string[] {
  return Array.from(
    new Set(
      trip?.expenses.map((expense) => (expense.currency ?? "USD").toUpperCase()) ?? [],
    ),
  );
}

function formatSettlementAmount(currency: string, amount: number): string {
  return `${currency} ${amount.toFixed(2)}`;
}

export default function SettlementPage() {
  const { tripId } = useParams();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const currencyCodes = expenseCurrencyCodes(trip);
  const settlementCurrency =
    currencyCodes.length <= 1 ? currencyCodes[0] ?? "USD" : null;

  useEffect(() => {
    async function loadSettlements() {
      if (!tripId) return;
      setIsLoading(true);
      setError(null);
      try {
        const [nextTrip, settlementSummary] = await Promise.all([
          getTrip(tripId),
          getSettlements(tripId),
        ]);
        setTrip(nextTrip);
        setSettlements(settlementSummary.settlements);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load settlements");
      } finally {
        setIsLoading(false);
      }
    }

    void loadSettlements();
  }, [tripId]);

  if (isLoading) {
    return <p className="empty-state">Loading settlements...</p>;
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Settlements</p>
          <h1>{trip?.name ?? "Trip"}</h1>
        </div>
        {trip ? (
          <Link className="secondary-button" to={`/trips/${trip.id}`}>
            Back to trip
          </Link>
        ) : null}
      </header>

      {error ? <div className="alert">{error}</div> : null}

      <section className="panel">
        <div className="panel-heading">
          <h2>Simplified Payments</h2>
          <span className="muted">{settlements.length} payments</span>
        </div>

        {settlements.length === 0 ? (
          <p className="empty-state">Everyone is settled.</p>
        ) : settlementCurrency === null ? (
          <p className="empty-state">
            Settlements are hidden for mixed-currency trips until exchange-rate
            conversion is supported.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>From</th>
                  <th>To</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {settlements.map((settlement) => (
                  <tr
                    key={`${settlement.from_participant_id}-${settlement.to_participant_id}`}
                  >
                    <td>{settlement.from_name}</td>
                    <td>{settlement.to_name}</td>
                    <td>
                      {formatSettlementAmount(settlementCurrency, settlement.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
