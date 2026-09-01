import argparse
import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.orm_models import (
    Expense,
    ExpenseCategory,
    ExpenseShare,
    ExpenseType,
    MemberRole,
    Trip,
    TripMember,
)
from app.services.calculations import split_cents_evenly


BACKEND_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BACKEND_DIR / "app" / "data" / "trips.json"


def load_json_data() -> dict[str, Any]:
    with JSON_PATH.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def amount_to_cents(value: float) -> int:
    decimal_amount = Decimal(str(value))

    return int(
        (
            decimal_amount * Decimal("100")
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )

def print_summary(data: dict[str, Any]) -> None:
    trips = [
        trip
        for trip in data.get("trips", [])
        if trip["name"] != "123"
    ]

    participant_count = sum(
        len(trip.get("participants", []))
        for trip in trips
    )
    expense_count = sum(
        len(trip.get("expenses", []))
        for trip in trips
    )

    print(f"Source:{JSON_PATH}")
    print(f"Trips:{len(trips)}")
    print(f"Participants:{participant_count}")
    print(f"Expenses:{expense_count}")


def validate_data(data: dict[str, Any]) -> None:
    trip_ids: set[UUID] = set()
    participant_ids: set[UUID] = set()
    expense_ids: set[UUID] = set()

    valid_expense_types = {
        "shared",
        "personal",
    }
    valid_categories = {
        "food",
        "hotel",
        "transportation",
        "gas",
        "tickets",
        "shopping",
        "other",
    }

    for trip in data.get("trips", []):
        if trip["name"] == "123":
            print(
                "Skipping invalid test trip: "
                f"{trip['name']}"
            )
            continue
        trip_id = UUID(trip["id"])

        if trip_id in trip_ids:
            raise ValueError(
                f"Duplicate trip ID: {trip_id}"
            )

        trip_ids.add(trip_id)
        date.fromisoformat(trip["start_date"])

        if trip.get("end_date") is not None:
            date.fromisoformat(trip["end_date"])

        current_member_ids: set[UUID] = set()

        for participant in trip.get(
            "participants",
            [],
        ):
            participant_id = UUID(participant["id"])

            if participant_id in participant_ids:
                raise ValueError(
                    "Duplicate participant ID: "
                    f"{participant_id}"
                )

            participant_ids.add(participant_id)
            current_member_ids.add(participant_id)

        for expense in trip.get("expenses", []):
            expense_id = UUID(expense["id"])

            if expense_id in expense_ids:
                raise ValueError(
                    f"Duplicate expense ID: {expense_id}"
                )

            expense_ids.add(expense_id)

            paid_by_id = UUID(expense["paid_by"])

            if paid_by_id not in current_member_ids:
                raise ValueError(
                    "Invalid paid_by reference in "
                    f"expense: {expense_id}"
                )

            for member_id_value in expense[
                "split_among"
            ]:
                member_id = UUID(member_id_value)

                if member_id not in current_member_ids:
                    raise ValueError(
                        "Invalid split member in "
                        f"expense: {expense_id}"
                    )

            if Decimal(str(expense["amount"])) <= 0:
                raise ValueError(
                    "Expense amount must be positive: "
                    f"{expense_id}"
                )

            if (
                expense["expense_type"]
                not in valid_expense_types
            ):
                raise ValueError(
                    "Invalid expense type: "
                    f"{expense_id}"
                )

            if expense["category"] not in valid_categories:
                raise ValueError(
                    "Invalid expense category: "
                    f"{expense_id}"
                )

            date.fromisoformat(expense["date"])

    print("Validation passed.")


def import_to_database(
    data: dict[str, Any],
    db: Session,
) -> None:
    existing_trip_count = db.scalar(
        select(func.count()).select_from(Trip)
    )

    if existing_trip_count != 0:
        raise RuntimeError(
            "Import stopped: the trips table is not empty."
        )

    for trip_data in data.get("trips", []):
        if trip_data["name"] == "123":
            continue

        trip_id = UUID(trip_data["id"])

        trip = Trip(
            id=trip_id,
            name=trip_data["name"],
            start_date=parse_date(
                trip_data["start_date"]
            ),
            end_date=(
                parse_date(trip_data["end_date"])
                if trip_data.get("end_date") is not None
                else None
            ),
            created_at=parse_datetime(
                trip_data["created_at"]
            ),
            updated_at=parse_datetime(
                trip_data["updated_at"]
            ),
        )
        db.add(trip)

        for participant_data in trip_data.get(
            "participants",
            [],
        ):
            member = TripMember(
                id=UUID(participant_data["id"]),
                trip_id=trip_id,
                user_id=None,
                display_name=participant_data["name"],
                role=MemberRole.MEMBER,
            )
            db.add(member)

        for expense_data in trip_data.get(
            "expenses",
            [],
        ):
            expense_id = UUID(expense_data["id"])
            amount_cents = amount_to_cents(
                expense_data["amount"]
            )

            expense = Expense(
                id=expense_id,
                trip_id=trip_id,
                paid_by_id=UUID(
                    expense_data["paid_by"]
                ),
                title=expense_data["title"],
                amount_cents=amount_cents,
                expense_type=ExpenseType(
                    expense_data["expense_type"]
                ),
                category=ExpenseCategory(
                    expense_data["category"]
                ),
                expense_date=parse_date(
                    expense_data["date"]
                ),
                currency=expense_data["currency"],
                note=expense_data.get("note"),
                created_at=parse_datetime(
                    expense_data["created_at"]
                ),
                updated_at=parse_datetime(
                    expense_data["updated_at"]
                ),
            )
            db.add(expense)

            split_member_ids = [
                UUID(member_id)
                for member_id in expense_data[
                    "split_among"
                ]
            ]
            share_amounts = split_cents_evenly(
                amount_cents,
                split_member_ids,
            )

            for member_id, share_cents in (
                share_amounts.items()
            ):
                share = ExpenseShare(
                    expense_id=expense_id,
                    member_id=member_id,
                    amount_cents=share_cents,
                )
                db.add(share)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import legacy TripSplit JSON data "
            "into PostgreSQL."
        )
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write the validated data to PostgreSQL.",
    )
    arguments = parser.parse_args()

    data = load_json_data()
    validate_data(data)
    print_summary(data)

    if not arguments.commit:
        print("Mode: preview only")
        print("No database changes were made.")
        return

    print("Mode: commit")

    with SessionLocal() as db:
        try:
            import_to_database(data, db)
            db.commit()
        except Exception:
            db.rollback()
            raise

    print("Import completed successfully.")


if __name__ == "__main__":
    main()