from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.orm_models import Expense, ExpenseShare, Trip, TripMember
from app.schemas import ParticipantCreate, ParticipantRead


router = APIRouter(
    prefix="/trips/{trip_id}/participants",
    tags=["participants"],
)


def find_trip_or_404(
    db: Session,
    trip_id: UUID,
) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return trip


def find_member_or_404(
    db: Session,
    trip_id: UUID,
    participant_id: UUID,
) -> TripMember:
    statement = select(TripMember).where(
        TripMember.id == participant_id,
        TripMember.trip_id == trip_id,
    )
    member = db.scalar(statement)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )
    return member


@router.get("", response_model=list[ParticipantRead])
def list_participants(
    trip_id: UUID,
    db: Session = Depends(get_db),
) -> list[TripMember]:
    find_trip_or_404(db, trip_id)

    statement = (
        select(TripMember)
        .where(TripMember.trip_id == trip_id)
        .order_by(TripMember.created_at)
    )
    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
def create_participant(
    trip_id: UUID,
    payload: ParticipantCreate,
    db: Session = Depends(get_db),
) -> TripMember:
    trip = find_trip_or_404(db, trip_id)

    member = TripMember(
        trip_id=trip.id,
        display_name=payload.name,
    )
    trip.updated_at = datetime.now(UTC)

    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.delete(
    "/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_participant(
    trip_id: UUID,
    participant_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    trip = find_trip_or_404(db, trip_id)
    member = find_member_or_404(
        db,
        trip_id,
        participant_id,
    )

    paid_expense_id = db.scalar(
        select(Expense.id)
        .where(Expense.paid_by_id == participant_id)
        .limit(1)
    )
    if paid_expense_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Participant paid for one or more expenses",
        )

    expense_share_id = db.scalar(
        select(ExpenseShare.id)
        .where(ExpenseShare.member_id == participant_id)
        .limit(1)
    )
    if expense_share_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Participant is included in one or more expense splits",
        )

    trip.updated_at = datetime.now(UTC)
    db.delete(member)
    db.commit()
