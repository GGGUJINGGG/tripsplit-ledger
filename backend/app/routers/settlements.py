from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.orm_models import Expense, Trip
from app.schemas import SettlementSummary
from app.services.settlements import simplify_settlements


router = APIRouter(
    prefix="/trips/{trip_id}/settlements",
    tags=["settlements"],
)


@router.get("", response_model=SettlementSummary)
def get_settlements(
    trip_id: UUID,
    db: Session = Depends(get_db),
) -> SettlementSummary:
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

    return simplify_settlements(trip)