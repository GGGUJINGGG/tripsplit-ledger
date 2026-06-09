from fastapi import APIRouter, HTTPException, status

from app.schemas import DashboardSummary
from app.services.calculations import build_dashboard_summary
from app.storage import load_data


router = APIRouter(prefix="/trips/{trip_id}/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardSummary)
def get_dashboard(trip_id: str) -> DashboardSummary:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            return build_dashboard_summary(trip)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
