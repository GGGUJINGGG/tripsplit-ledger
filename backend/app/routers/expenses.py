from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.models import Expense, ExpenseType
from app.schemas import ExpenseCreate, ExpenseUpdate
from app.storage import load_data, save_data


router = APIRouter(prefix="/trips/{trip_id}/expenses", tags=["expenses"])


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def validate_expense_people(
    participant_ids: set[str],
    paid_by: str,
    split_among: list[str],
) -> None:
    if paid_by not in participant_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="paid_by must be an existing participant",
        )

    unknown_splitters = sorted(set(split_among) - participant_ids)
    if unknown_splitters:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"split_among contains unknown participants: {unknown_splitters}",
        )


@router.get("", response_model=list[Expense])
def list_expenses(trip_id: str) -> list[Expense]:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            return trip.expenses

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.post("", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(trip_id: str, payload: ExpenseCreate) -> Expense:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            participant_ids = {participant.id for participant in trip.participants}
            split_among = (
                [payload.paid_by]
                if payload.expense_type == ExpenseType.PERSONAL
                else payload.split_among
            )
            validate_expense_people(participant_ids, payload.paid_by, split_among)

            now = utc_now()
            expense = Expense(
                id=str(uuid4()),
                trip_id=trip_id,
                title=payload.title,
                amount=payload.amount,
                paid_by=payload.paid_by,
                split_among=split_among,
                expense_type=payload.expense_type,
                category=payload.category,
                date=payload.date,
                currency=payload.currency,
                note=payload.note,
                created_at=now,
                updated_at=now,
            )
            trip.expenses.append(expense)
            trip.updated_at = now
            save_data(data)
            return expense

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.get("/{expense_id}", response_model=Expense)
def get_expense(trip_id: str, expense_id: str) -> Expense:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            for expense in trip.expenses:
                if expense.id == expense_id:
                    return expense
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found",
            )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.put("/{expense_id}", response_model=Expense)
def update_expense(trip_id: str, expense_id: str, payload: ExpenseUpdate) -> Expense:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            participant_ids = {participant.id for participant in trip.participants}
            for index, expense in enumerate(trip.expenses):
                if expense.id == expense_id:
                    updates = payload.model_dump(exclude_unset=True)
                    paid_by = updates.get("paid_by", expense.paid_by)
                    expense_type = updates.get("expense_type", expense.expense_type)
                    split_among = (
                        [paid_by]
                        if expense_type == ExpenseType.PERSONAL
                        else updates.get("split_among", expense.split_among)
                    )
                    validate_expense_people(participant_ids, paid_by, split_among)
                    updates["split_among"] = split_among

                    updated_expense = expense.model_copy(
                        update={**updates, "updated_at": utc_now()}
                    )
                    trip.expenses[index] = updated_expense
                    trip.updated_at = updated_expense.updated_at
                    save_data(data)
                    return updated_expense

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found",
            )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(trip_id: str, expense_id: str) -> None:
    data = load_data()
    for trip in data.trips:
        if trip.id == trip_id:
            original_count = len(trip.expenses)
            trip.expenses = [
                expense for expense in trip.expenses if expense.id != expense_id
            ]

            if len(trip.expenses) == original_count:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Expense not found",
                )

            trip.updated_at = utc_now()
            save_data(data)
            return

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
