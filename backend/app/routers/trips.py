from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.orm_models import MemberRole, Trip, TripMember, User
from app.schemas import ExpenseRead, TripCreate, TripRead, TripUpdate
from app.auth_dependencies import get_current_user
from app.services.calculations import is_expense_visible


router = APIRouter(
    prefix="/trips",
    tags=["trips"],
    dependencies=[Depends(get_current_user)],
)


def find_trip_or_404(
    db: Session,
    trip_id: UUID,
    current_user: User,
) -> Trip:
    statement = (
        select(Trip)
        .join(TripMember)
        .where(
            Trip.id == trip_id,
            TripMember.user_id == current_user.id,
        )
    )
    trip = db.scalar(statement)

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    return trip


def require_trip_owner(
    db: Session,
    trip_id: UUID,
    current_user: User,
) -> Trip:
    trip = find_trip_or_404(db, trip_id, current_user)

    membership = db.scalar(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user.id,
        )
    )
    if membership.role != MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the trip owner can perform this action",
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
    current_user: User = Depends(get_current_user),
) -> list[Trip]:
    statement = (
        select(Trip)
        .join(TripMember)
        .where(TripMember.user_id == current_user.id)
        .order_by(Trip.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.post(
        "",
        response_model=TripRead,
        status_code=status.HTTP_201_CREATED,
)
def create_trip(
    payload: TripCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Trip:
    trip = Trip(
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    trip.members.append(
        TripMember(
            user=current_user,
            display_name=current_user.display_name,
            role=MemberRole.OWNER,
        )
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripRead:
    trip = find_trip_or_404(db, trip_id, current_user)
    trip_read = TripRead.model_validate(trip)
    trip_read.expenses = [
        ExpenseRead.model_validate(expense)
        for expense in trip.expenses
        if is_expense_visible(expense, current_user.id)
    ]
    return trip_read


@router.put("/{trip_id}", response_model=TripRead)
def update_trip(
    trip_id: UUID,
    payload: TripUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Trip:
    trip = require_trip_owner(db, trip_id, current_user)
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
    current_user: User = Depends(get_current_user),
) -> None:
    trip = require_trip_owner(db, trip_id, current_user)
    db.delete(trip)
    db.commit()
