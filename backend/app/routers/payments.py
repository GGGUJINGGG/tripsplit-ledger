from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_dependencies import get_current_user
from app.database import get_db
from app.orm_models import Payment, TripMember, User
from app.routers.trips import find_trip_or_404
from app.schemas import PaymentCreate, PaymentRead
from app.services.calculations import amount_to_cents


router = APIRouter(
    prefix="/trips/{trip_id}/payments",
    tags=["payments"],
)


def find_payment_or_404(
    db: Session,
    trip_id: UUID,
    payment_id: UUID,
) -> Payment:
    statement = select(Payment).where(
        Payment.id == payment_id,
        Payment.trip_id == trip_id,
    )
    payment = db.scalar(statement)

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment


def get_participant_ids(db: Session, trip_id: UUID) -> set[UUID]:
    statement = select(TripMember.id).where(
        TripMember.trip_id == trip_id
    )
    return set(db.scalars(statement).all())


def validate_payment_participants(
    participant_ids: set[UUID],
    from_participant: UUID,
    to_participant: UUID,
) -> None:
    if from_participant not in participant_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="from_participant must be an existing participant",
        )
    if to_participant not in participant_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to_participant must be an existing participant",
        )


@router.get("", response_model=list[PaymentRead])
def list_payments(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Payment]:
    find_trip_or_404(db, trip_id, current_user)

    statement = (
        select(Payment)
        .where(Payment.trip_id == trip_id)
        .order_by(
            Payment.payment_date.desc(),
            Payment.created_at.desc(),
        )
    )
    return list(db.scalars(statement).all())


@router.post(
    "",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    trip_id: UUID,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    trip = find_trip_or_404(db, trip_id, current_user)
    validate_payment_participants(
        get_participant_ids(db, trip_id),
        payload.from_participant,
        payload.to_participant,
    )

    payment = Payment(
        trip_id=trip.id,
        from_member_id=payload.from_participant,
        to_member_id=payload.to_participant,
        amount_cents=amount_to_cents(payload.amount),
        currency=(payload.currency or "USD").upper(),
        payment_date=payload.date,
        note=payload.note,
    )

    trip.updated_at = datetime.now(UTC)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.delete(
    "/{payment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_payment(
    trip_id: UUID,
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    trip = find_trip_or_404(db, trip_id, current_user)
    payment = find_payment_or_404(db, trip_id, payment_id)

    trip.updated_at = datetime.now(UTC)
    db.delete(payment)
    db.commit()
