from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.models import Participant
from app.schemas import ParticipantCreate
from app.storage import load_data, save_data


router = APIRouter(prefix="/trips/{trip_id}/participants", tags=["participants"])


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@router.get("", response_model=list[Participant])
def list_participants(trip_id: str) -> list[Participant]:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            return trip.participants

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.post("", response_model=Participant, status_code=status.HTTP_201_CREATED)
def create_participant(trip_id: str, payload: ParticipantCreate) -> Participant:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            participant = Participant(id=str(uuid4()), name=payload.name)
            trip.participants.append(participant)
            trip.updated_at = utc_now()
            save_data(data)
            return participant

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(trip_id: str, participant_id: str) -> None:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            if any(expense.paid_by == participant_id for expense in trip.expenses):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Participant paid for one or more expenses",
                )

            if any(participant_id in expense.split_among for expense in trip.expenses):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Participant is included in one or more expense splits",
                )

            original_count = len(trip.participants)
            trip.participants = [
                participant
                for participant in trip.participants
                if participant.id != participant_id
            ]

            if len(trip.participants) == original_count:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Participant not found",
                )

            trip.updated_at = utc_now()
            save_data(data)
            return

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
