from fastapi import APIRouter, HTTPException, status

from app.schemas import SettlementSummary
from app.services.settlements import simplify_settlements
from app.storage import load_data


router = APIRouter(prefix="/trips/{trip_id}/settlements", tags=["settlements"])


@router.get("", response_model=SettlementSummary)
def get_settlements(trip_id: str) -> SettlementSummary:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            return simplify_settlements(trip)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
