import { Link } from "react-router-dom";

import type { Trip } from "../../types";

interface TripHeaderProps {
  trip: Trip;
}

export default function TripHeader({ trip }: TripHeaderProps) {
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
      <Link className="secondary-button" to={`/trips/${trip.id}/settlements`}>
        Settlements
      </Link>
    </header>
  );
}
