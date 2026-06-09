from collections import defaultdict

from app.models import ExpenseCategory, ExpenseType, Trip
from app.schemas import (
    CategorySpending,
    DailySpending,
    DashboardSummary,
    PersonAmount,
    PersonBalance,
)


def cents_to_float(cents: int) -> float:
    return round(cents / 100, 2)


def amount_to_cents(amount: float) -> int:
    return round(amount * 100)


def split_cents_evenly(amount_cents: int, participant_ids: list[str]) -> dict[str, int]:
    sorted_participant_ids = sorted(participant_ids)
    base_share, remainder = divmod(amount_cents, len(sorted_participant_ids))
    shares = {}

    for index, participant_id in enumerate(sorted_participant_ids):
        shares[participant_id] = base_share + (1 if index < remainder else 0)

    return shares


def paid_by_person_cents(trip: Trip, shared_only: bool = False) -> dict[str, int]:
    paid_totals = {participant.id: 0 for participant in trip.participants}

    for expense in trip.expenses:
        if shared_only and expense.expense_type != ExpenseType.SHARED:
            continue
        paid_totals[expense.paid_by] += amount_to_cents(expense.amount)

    return paid_totals


def owed_by_person_cents(trip: Trip) -> dict[str, int]:
    owed_totals = {participant.id: 0 for participant in trip.participants}

    for expense in trip.expenses:
        if expense.expense_type != ExpenseType.SHARED:
            continue
        amount_cents = amount_to_cents(expense.amount)
        shares = split_cents_evenly(amount_cents, expense.split_among)
        for participant_id, share_cents in shares.items():
            owed_totals[participant_id] += share_cents

    return owed_totals


def net_balances_cents(trip: Trip) -> dict[str, int]:
    paid_totals = paid_by_person_cents(trip, shared_only=True)
    owed_totals = owed_by_person_cents(trip)

    return {
        participant.id: paid_totals[participant.id] - owed_totals[participant.id]
        for participant in trip.participants
    }


def build_dashboard_summary(trip: Trip) -> DashboardSummary:
    category_totals: dict[ExpenseCategory, int] = defaultdict(int)
    daily_totals: dict[str, int] = defaultdict(int)

    for expense in trip.expenses:
        amount_cents = amount_to_cents(expense.amount)
        category_totals[expense.category] += amount_cents
        daily_totals[expense.date] += amount_cents

    paid_totals = paid_by_person_cents(trip)
    owed_totals = owed_by_person_cents(trip)
    balances = net_balances_cents(trip)
    participants_by_id = {
        participant.id: participant.name for participant in trip.participants
    }

    return DashboardSummary(
        total_trip_spending=cents_to_float(
            sum(amount_to_cents(expense.amount) for expense in trip.expenses)
        ),
        spending_by_category=[
            CategorySpending(category=category, amount=cents_to_float(amount))
            for category, amount in sorted(
                category_totals.items(),
                key=lambda item: (-item[1], item[0].value),
            )
        ],
        spending_by_day=[
            DailySpending(date=date, amount=cents_to_float(amount))
            for date, amount in sorted(daily_totals.items())
        ],
        paid_by_person=[
            PersonAmount(
                participant_id=participant_id,
                name=participants_by_id[participant_id],
                amount=cents_to_float(amount),
            )
            for participant_id, amount in paid_totals.items()
        ],
        owed_by_person=[
            PersonAmount(
                participant_id=participant_id,
                name=participants_by_id[participant_id],
                amount=cents_to_float(amount),
            )
            for participant_id, amount in owed_totals.items()
        ],
        net_balances=[
            PersonBalance(
                participant_id=participant_id,
                name=participants_by_id[participant_id],
                balance=cents_to_float(balance),
            )
            for participant_id, balance in balances.items()
        ],
    )
