from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.orm_models import Expense, Trip, TripMember, User
from app.schemas import DashboardSummary
from app.services.calculations import build_dashboard_summary
from app.auth_dependencies import get_current_user


router = APIRouter(
    prefix="/trips/{trip_id}/dashboard",
    tags=["dashboard"],
)


@router.get("", response_model=DashboardSummary)
def get_dashboard(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    statement = (
        select(Trip)
        .options(
            selectinload(Trip.members),
            selectinload(Trip.expenses).selectinload(
                Expense.shares
            ),
        )
        .where(
            Trip.id == trip_id,
            Trip.members.any(TripMember.user_id == current_user.id),
        )
    )
    trip = db.scalar(statement)

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    return build_dashboard_summary(trip)
