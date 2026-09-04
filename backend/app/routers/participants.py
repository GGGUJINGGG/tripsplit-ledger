from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.email import send_trip_invite_email
from app.orm_models import (
    Expense,
    ExpenseShare,
    MemberRole,
    TripMember,
    User,
)
from app.schemas import MemberInvite, ParticipantCreate, ParticipantRead
from app.auth_dependencies import get_current_user
from app.routers.trips import find_trip_or_404, require_trip_owner


router = APIRouter(
    prefix="/trips/{trip_id}/participants",
    tags=["participants"],
)


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
    current_user: User = Depends(get_current_user),
) -> list[TripMember]:
    find_trip_or_404(db, trip_id, current_user)

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
    current_user: User = Depends(get_current_user),
) -> TripMember:
    trip = find_trip_or_404(db, trip_id, current_user)

    member = TripMember(
        trip_id=trip.id,
        display_name=payload.name,
    )
    trip.updated_at = datetime.now(UTC)

    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post(
    "/invite",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    trip_id: UUID,
    payload: MemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripMember:
    trip = require_trip_owner(db, trip_id, current_user)

    normalized_email = str(payload.email).strip().lower()
    invited_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if invited_user is not None:
        already_member = db.scalar(
            select(TripMember).where(
                TripMember.trip_id == trip_id,
                TripMember.user_id == invited_user.id,
            )
        )
        if already_member is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this trip",
            )

    existing_invite = db.scalar(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.invited_email == normalized_email,
            TripMember.user_id.is_(None),
        )
    )
    if existing_invite is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email has already been invited to this trip",
        )

    # Whether or not this email already has an account, an invite is
    # just a pending placeholder — visible in the trip right away, but
    # not a real membership until it's explicitly accepted. An
    # unregistered email accepts by registering (see
    # register_user()); a registered one accepts from their
    # pending-invitations list (see routers/invitations.py).
    member = TripMember(
        trip_id=trip.id,
        display_name=normalized_email,
        invited_email=normalized_email,
        role=MemberRole.MEMBER,
    )
    trip.updated_at = datetime.now(UTC)

    db.add(member)
    db.commit()
    db.refresh(member)

    if invited_user is not None:
        action_url = f"{settings.frontend_base_url.rstrip('/')}/"
    else:
        action_url = (
            f"{settings.frontend_base_url.rstrip('/')}"
            f"/register?email={quote(normalized_email)}"
        )
    send_trip_invite_email(normalized_email, trip.name, action_url)

    return member


@router.delete(
    "/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_participant(
    trip_id: UUID,
    participant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    trip = find_trip_or_404(db, trip_id, current_user)
    member = find_member_or_404(
        db,
        trip_id,
        participant_id,
    )

    if member.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trip owner cannot be deleted",
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