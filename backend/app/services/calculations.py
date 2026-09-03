from collections import defaultdict
from typing import Any

from app.orm_models import ExpenseCategory, ExpenseType
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


def get_participants(trip: Any) -> list[Any]:
    if hasattr(trip, "participants"):
        return trip.participants
    return trip.members


def get_participant_name(participant: Any) -> str:
    if hasattr(participant, "name"):
        return participant.name
    return participant.display_name


def get_paid_by_id(expense: Any) -> Any:
    if hasattr(expense, "paid_by_id"):
        return expense.paid_by_id
    return expense.paid_by


def is_shared_expense(expense: Any) -> bool:
    return str(expense.expense_type) == ExpenseType.SHARED.value


def is_expense_visible(expense: Any, current_user_id: Any) -> bool:
    """Shared expenses are visible to the whole trip; personal expenses
    are visible only to the member who paid for them, and only when
    that member is the currently authenticated user. A guest payer has
    no user_id, so their personal expenses are visible to no one."""
    if is_shared_expense(expense):
        return True
    if current_user_id is None:
        return False
    payer = expense.paid_by
    payer_user_id = getattr(payer, "user_id", None) if payer is not None else None
    return payer_user_id is not None and payer_user_id == current_user_id


class VisibleExpensesView:
    """Duck-typed stand-in for a Trip whose .expenses have already been
    filtered to what the current user is allowed to see. Everything in
    this module only reads .members/.participants and .expenses off
    whatever trip-like object it's given."""

    def __init__(self, members: list[Any], expenses: list[Any]) -> None:
        self.members = members
        self.expenses = expenses


def filter_visible_expenses(trip: Any, current_user_id: Any) -> VisibleExpensesView:
    return VisibleExpensesView(
        members=get_participants(trip),
        expenses=[
            expense
            for expense in trip.expenses
            if is_expense_visible(expense, current_user_id)
        ],
    )


def split_cents_evenly(
    amount_cents: int,
    participant_ids: list[Any],
) -> dict[Any, int]:
    sorted_participant_ids = sorted(
        participant_ids,
        key=str,
    )
    base_share, remainder = divmod(
        amount_cents,
        len(sorted_participant_ids),
    )
    shares = {}

    for index, participant_id in enumerate(
        sorted_participant_ids
    ):
        shares[participant_id] = base_share + (
            1 if index < remainder else 0
        )

    return shares


def paid_by_person_cents(
    trip: Any,
    shared_only: bool = False,
) -> dict[Any, int]:
    participants = get_participants(trip)
    paid_totals = {
        participant.id: 0
        for participant in participants
    }

    for expense in trip.expenses:
        if shared_only and not is_shared_expense(expense):
            continue

        paid_totals[get_paid_by_id(expense)] += (
            amount_to_cents(expense.amount)
        )

    return paid_totals


def owed_by_person_cents(trip: Any) -> dict[Any, int]:
    participants = get_participants(trip)
    owed_totals = {
        participant.id: 0
        for participant in participants
    }

    for expense in trip.expenses:
        if not is_shared_expense(expense):
            continue

        amount_cents = amount_to_cents(expense.amount)
        shares = split_cents_evenly(
            amount_cents,
            expense.split_among,
        )
        for participant_id, share_cents in shares.items():
            owed_totals[participant_id] += share_cents

    return owed_totals


def net_balances_cents(trip: Any) -> dict[Any, int]:
    participants = get_participants(trip)
    paid_totals = paid_by_person_cents(
        trip,
        shared_only=True,
    )
    owed_totals = owed_by_person_cents(trip)

    return {
        participant.id: (
            paid_totals[participant.id]
            - owed_totals[participant.id]
        )
        for participant in participants
    }


def build_dashboard_summary(trip: Any) -> DashboardSummary:
    category_totals: dict[ExpenseCategory, int] = defaultdict(int)
    daily_totals: dict[str, int] = defaultdict(int)

    for expense in trip.expenses:
        amount_cents = amount_to_cents(expense.amount)
        category = ExpenseCategory(str(expense.category))
        category_totals[category] += amount_cents
        daily_totals[str(expense.date)] += amount_cents

    participants = get_participants(trip)
    paid_totals = paid_by_person_cents(trip)
    owed_totals = owed_by_person_cents(trip)
    balances = net_balances_cents(trip)
    participants_by_id = {
        participant.id: get_participant_name(participant)
        for participant in participants
    }

    return DashboardSummary(
        total_trip_spending=cents_to_float(
            sum(
                amount_to_cents(expense.amount)
                for expense in trip.expenses
            )
        ),
        spending_by_category=[
            CategorySpending(
                category=category,
                amount=cents_to_float(amount),
            )
            for category, amount in sorted(
                category_totals.items(),
                key=lambda item: (
                    -item[1],
                    item[0].value,
                ),
            )
        ],
        spending_by_day=[
            DailySpending(
                date=date_value,
                amount=cents_to_float(amount),
            )
            for date_value, amount in sorted(
                daily_totals.items()
            )
        ],
        paid_by_person=[
            PersonAmount(
                participant_id=str(participant_id),
                name=participants_by_id[participant_id],
                amount=cents_to_float(amount),
            )
            for participant_id, amount in paid_totals.items()
        ],
        owed_by_person=[
            PersonAmount(
                participant_id=str(participant_id),
                name=participants_by_id[participant_id],
                amount=cents_to_float(amount),
            )
            for participant_id, amount in owed_totals.items()
        ],
        net_balances=[
            PersonBalance(
                participant_id=str(participant_id),
                name=participants_by_id[participant_id],
                balance=cents_to_float(balance),
            )
            for participant_id, balance in balances.items()
        ],
    )