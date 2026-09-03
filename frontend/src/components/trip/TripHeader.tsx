import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Pencil, Trash2 } from "lucide-react";

import type { Trip, TripUpdate } from "../../types";

interface TripHeaderProps {
  trip: Trip;
  currentUserId?: string;
  isSaving: boolean;
  onRename: (payload: TripUpdate) => Promise<boolean>;
  onDelete: () => void;
}

export default function TripHeader({
  trip,
  currentUserId,
  isSaving,
  onRename,
  onDelete,
}: TripHeaderProps) {
  const isOwner = trip.participants.some(
    (participant) => participant.user_id === currentUserId && participant.role === "owner",
  );

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(trip.name);
  const [startDate, setStartDate] = useState(trip.start_date);
  const [endDate, setEndDate] = useState(trip.end_date ?? "");

  function startEditing() {
    setName(trip.name);
    setStartDate(trip.start_date);
    setEndDate(trip.end_date ?? "");
    setIsEditing(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const succeeded = await onRename({
      name: name.trim(),
      start_date: startDate,
      end_date: endDate || undefined,
    });
    if (succeeded) {
      setIsEditing(false);
    }
  }

  if (isEditing) {
    return (
      <header className="page-header">
        <form className="form-grid compact" onSubmit={handleSubmit}>
          <label htmlFor="trip-header-name">
            Trip name
            <input
              id="trip-header-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </label>
          <label htmlFor="trip-header-start-date">
            Start date
            <input
              id="trip-header-start-date"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              required
            />
          </label>
          <label htmlFor="trip-header-end-date">
            End date
            <input
              id="trip-header-end-date"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              min={startDate || undefined}
            />
          </label>
          <div className="header-actions">
            <button className="primary-button" type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save changes"}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setIsEditing(false)}
              disabled={isSaving}
            >
              Cancel
            </button>
          </div>
        </form>
      </header>
    );
  }

  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">Trip Detail</p>
        <h1>{trip.name}</h1>
        <p className="muted">
          {trip.start_date}
          {trip.end_date ? ` to ${trip.end_date}` : ""}
        </p>
      </div>
      <div className="header-actions">
        {isOwner ? (
          <>
            <button
              className="secondary-button"
              type="button"
              onClick={startEditing}
            >
              <Pencil size={16} />
              Edit trip
            </button>
            <button
              className="secondary-button danger"
              type="button"
              onClick={onDelete}
              disabled={isSaving}
            >
              <Trash2 size={16} />
              Delete trip
            </button>
          </>
        ) : null}
        <Link className="secondary-button" to={`/trips/${trip.id}/settlements`}>
          Settlements
        </Link>
      </div>
    </header>
  );
}
