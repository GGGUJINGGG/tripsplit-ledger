import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";

import { createTrip, getTrips } from "../api/trips";
import type { Trip } from "../types";

export default function TripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadTrips() {
    setIsLoading(true);
    setError(null);
    try {
      setTrips(await getTrips());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load trips");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadTrips();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !startDate) {
      setError("Trip name and start date are required.");
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      await createTrip({
        name: name.trim(),
        start_date: startDate,
        end_date: endDate || undefined,
      });
      setName("");
      setStartDate("");
      setEndDate("");
      await loadTrips();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create trip");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Trips</p>
          <h1>Trip Ledger</h1>
        </div>
      </header>

      {error ? <div className="alert">{error}</div> : null}

      <div className="content-grid two-columns">
        <section className="panel">
          <div className="panel-heading">
            <h2>Create Trip</h2>
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label htmlFor="trip-name">
              Trip name
              <input
                id="trip-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Iceland Road Trip"
              />
            </label>
            <label htmlFor="trip-start-date">
              Start date
              <input
                id="trip-start-date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                placeholder="2026-07-01"
              />
            </label>
            <label htmlFor="trip-end-date">
              End date
              <input
                id="trip-end-date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                placeholder="2026-07-04"
              />
            </label>
            <button className="primary-button" type="submit" disabled={isSaving}>
              <Plus size={18} />
              {isSaving ? "Creating..." : "Create trip"}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>All Trips</h2>
            <span className="muted">{trips.length} total</span>
          </div>

          {isLoading ? (
            <p className="empty-state">Loading trips...</p>
          ) : trips.length === 0 ? (
            <p className="empty-state">No trips yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Dates</th>
                    <th>People</th>
                    <th>Expenses</th>
                  </tr>
                </thead>
                <tbody>
                  {trips.map((trip) => (
                    <tr key={trip.id}>
                      <td>
                        <Link className="table-link" to={`/trips/${trip.id}`}>
                          {trip.name}
                        </Link>
                      </td>
                      <td>
                        {trip.start_date}
                        {trip.end_date ? ` to ${trip.end_date}` : ""}
                      </td>
                      <td>{trip.participants.length}</td>
                      <td>{trip.expenses.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
