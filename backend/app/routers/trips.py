from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.models import Trip
from app.schemas import TripCreate, TripUpdate
from app.storage import load_data, save_data


router = APIRouter(prefix="/trips", tags=["trips"])


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def find_trip_or_404(trip_id: str) -> Trip:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            return trip
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.get("", response_model=list[Trip])
def list_trips() -> list[Trip]:
    data = load_data()
    return data.trips


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate) -> Trip:
    data = load_data()
    now = utc_now()
    trip = Trip(
        id=str(uuid4()),
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_at=now,
        updated_at=now,
    )
    data.trips.append(trip)
    save_data(data)
    return trip


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: str) -> Trip:
    return find_trip_or_404(trip_id)


@router.put("/{trip_id}", response_model=Trip)
def update_trip(trip_id: str, payload: TripUpdate) -> Trip:
    data = load_data()
    for index, trip in enumerate(data.trips):
        if trip.id == trip_id:
            updates = payload.model_dump(exclude_unset=True)
            updated_trip = trip.model_copy(
                update={**updates, "updated_at": utc_now()}
            )
            data.trips[index] = updated_trip
            save_data(data)
            return updated_trip

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: str) -> None:
    data = load_data()
    original_count = len(data.trips)
    data.trips = [trip for trip in data.trips if trip.id != trip_id]

    if len(data.trips) == original_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    save_data(data)
