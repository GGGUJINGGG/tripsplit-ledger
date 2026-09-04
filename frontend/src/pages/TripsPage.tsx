import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Plus, X } from "lucide-react";

import { acceptInvitation, declineInvitation, getMyInvitations } from "../api/invitations";
import { createTrip, getTrips } from "../api/trips";
import type { PendingInvitation, Trip } from "../types";

export default function TripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [invitations, setInvitations] = useState<PendingInvitation[]>([]);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [respondingToId, setRespondingToId] = useState<string | null>(null);
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

  async function loadInvitations() {
    try {
      setInvitations(await getMyInvitations());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load invitations");
    }
  }

  useEffect(() => {
    void loadTrips();
    void loadInvitations();
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

  async function handleAccept(invitation: PendingInvitation) {
    setRespondingToId(invitation.id);
    setError(null);
    try {
      await acceptInvitation(invitation.id);
      await Promise.all([loadTrips(), loadInvitations()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to accept invitation");
    } finally {
      setRespondingToId(null);
    }
  }

  async function handleDecline(invitation: PendingInvitation) {
    setRespondingToId(invitation.id);
    setError(null);
    try {
      await declineInvitation(invitation.id);
      await loadInvitations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to decline invitation");
    } finally {
      setRespondingToId(null);
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

      {invitations.length > 0 ? (
        <section className="panel">
          <div className="panel-heading">
            <h2>Pending Invites</h2>
          </div>
          <div className="list-stack">
            {invitations.map((invitation) => (
              <div className="list-row" key={invitation.id}>
                <span>You've been invited to "{invitation.trip_name}"</span>
                <div className="header-actions">
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => void handleAccept(invitation)}
                    disabled={respondingToId === invitation.id}
                    aria-label={`Accept invite to ${invitation.trip_name}`}
                    title="Accept"
                  >
                    <Check size={16} />
                  </button>
                  <button
                    className="ghost-icon-button"
                    type="button"
                    onClick={() => void handleDecline(invitation)}
                    disabled={respondingToId === invitation.id}
                    aria-label={`Decline invite to ${invitation.trip_name}`}
                    title="Decline"
                  >
                    <X size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

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
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
              <span className="field-hint">Stored as YYYY-MM-DD.</span>
            </label>
            <label htmlFor="trip-end-date">
              End date
              <input
                id="trip-end-date"
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                min={startDate || undefined}
              />
              <span className="field-hint">Optional. Cannot be before start date.</span>
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
