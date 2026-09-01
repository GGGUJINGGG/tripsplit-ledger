from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.orm_models import Expense, Trip
from app.schemas import DashboardSummary
from app.services.calculations import build_dashboard_summary


router = APIRouter(
    prefix="/trips/{trip_id}/dashboard",
    tags=["dashboard"],
)


@router.get("", response_model=DashboardSummary)
def get_dashboard(
    trip_id: UUID,
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
        .where(Trip.id == trip_id)
    )
    trip = db.scalar(statement)

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    return build_dashboard_summary(trip)
