from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.orm_models import Trip
from app.schemas import TripCreate, TripRead, TripUpdate


router = APIRouter(prefix="/trips", tags=["trips"])


def find_trip_or_404(db: Session, trip_id: UUID) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return trip


def to_422(validation_error: ValidationError) -> HTTPException:
    errors = validation_error.errors(
        include_url=False,
        include_input=False,
    )
    for error in errors:
        ctx = error.get("ctx")
        if ctx and "error" in ctx:
            ctx["error"] = str(ctx["error"])

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=errors,
    )


def normalize_trip_updates(
        trip: Trip,
        payload: TripUpdate,
    ) -> dict:
    updates = payload.model_dump(exclude_unset=True)

    try:
        TripCreate(
            name=updates.get("name", trip.name),
            start_date=updates.get("start_date", trip.start_date),
            end_date=updates.get("end_date", trip.end_date),
        )
    except ValidationError as exc:
        raise to_422(exc) from exc

    return updates


@router.get("", response_model=list[TripRead])
def list_trips(
    db: Session = Depends(get_db),
) -> list[Trip]:
    statement = select(Trip).order_by(Trip.created_at.desc())
    return list(db.scalars(statement).all())


@router.post(
        "",
        response_model=TripRead,
        status_code=status.HTTP_201_CREATED,
)
def create_trip(
    payload: TripCreate,
    db: Session = Depends(get_db),
) -> Trip:
    trip = Trip(
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
) -> Trip:
    return find_trip_or_404(db, trip_id)


@router.put("/{trip_id}", response_model=TripRead)
def update_trip(
    trip_id: UUID,
    payload: TripUpdate,
    db: Session = Depends(get_db),
) -> Trip:
    trip = find_trip_or_404(db, trip_id)
    updates = normalize_trip_updates(trip, payload)

    for field, value in updates.items():
        setattr(trip, field, value)

    db.commit()
    db.refresh(trip)
    return trip


@router.delete(
        "/{trip_id}",
        status_code=status.HTTP_204_NO_CONTENT,
)
def delete_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    trip = find_trip_or_404(db, trip_id)
    db.delete(trip)
    db.commit()
