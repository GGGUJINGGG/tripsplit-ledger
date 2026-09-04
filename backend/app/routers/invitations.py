from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth_dependencies import get_current_user
from app.database import get_db
from app.orm_models import TripMember, User
from app.schemas import ParticipantRead, PendingInvitation


router = APIRouter(
    prefix="/invitations",
    tags=["invitations"],
)


def _find_pending_invitation_or_404(
    db: Session,
    invitation_id: UUID,
    current_user: User,
) -> TripMember:
    member = db.scalar(
        select(TripMember).where(
            TripMember.id == invitation_id,
            TripMember.invited_email == current_user.email,
            TripMember.user_id.is_(None),
        )
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    return member


@router.get("", response_model=list[PendingInvitation])
def list_my_pending_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PendingInvitation]:
    statement = (
        select(TripMember)
        .options(selectinload(TripMember.trip))
        .where(
            TripMember.invited_email == current_user.email,
            TripMember.user_id.is_(None),
        )
        .order_by(TripMember.created_at.desc())
    )
    members = db.scalars(statement).all()
    return [
        PendingInvitation(
            id=member.id,
            trip_id=member.trip_id,
            trip_name=member.trip.name,
            invited_at=member.created_at,
        )
        for member in members
    ]


@router.post("/{invitation_id}/accept", response_model=ParticipantRead)
def accept_invitation(
    invitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripMember:
    member = _find_pending_invitation_or_404(db, invitation_id, current_user)

    member.user_id = current_user.id
    member.display_name = current_user.display_name
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def decline_invitation(
    invitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    member = _find_pending_invitation_or_404(db, invitation_id, current_user)

    db.delete(member)
    db.commit()
