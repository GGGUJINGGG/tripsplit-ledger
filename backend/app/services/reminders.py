from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.email import send_settlement_reminder_email
from app.orm_models import Trip, TripMember
from app.services.settlements import simplify_settlements


def _debts_by_debtor_id(trip: Trip) -> dict[str, list[dict[str, Any]]]:
    debts_by_debtor: dict[str, list[dict[str, Any]]] = {}
    for settlement in simplify_settlements(trip).settlements:
        debts_by_debtor.setdefault(settlement.from_participant_id, []).append(
            {
                "to_name": settlement.to_name,
                "amount": settlement.amount,
                "currency": settlement.currency,
            }
        )
    return debts_by_debtor


def _remind_trip_debtors(trip: Trip) -> bool:
    """Email every debtor on this trip who has an account to email.
    Returns whether the trip had any outstanding debt at all (true even
    if every debtor turned out to be an unreachable guest) — the
    signal the caller uses to log how many trips were actually reminded
    versus just checked."""
    debts_by_debtor = _debts_by_debtor_id(trip)
    if not debts_by_debtor:
        return False  # everyone's settled — nothing to remind anyone about

    trip_url = f"{settings.frontend_base_url.rstrip('/')}/trips/{trip.id}"
    members_by_id = {str(member.id): member for member in trip.members}

    for participant_id, debts in debts_by_debtor.items():
        member = members_by_id.get(participant_id)
        # A guest invited by email but not yet registered (or, in
        # theory, an id simplify_settlements returned that isn't a
        # current member) has no account to email.
        if member is None or member.user is None:
            continue
        send_settlement_reminder_email(
            member.user.email,
            trip.name,
            debts,
            trip_url,
        )

    return True


def _trip_query():
    return select(Trip).options(
        selectinload(Trip.members).selectinload(TripMember.user),
        selectinload(Trip.expenses),
        selectinload(Trip.payments),
    )


def send_due_settlement_reminders(db: Session, today: date | None = None) -> int:
    """Email every trip participant who still owes money on a trip that's
    due for a reminder today. Meant to run once a day (see
    app/scripts/send_settlement_reminders.py); two independent triggers:

    - A trip with an end_date gets exactly one reminder, the day after
      it ends — tracked by end_date_reminder_sent_at so it never fires
      twice even if this runs more than once that day.
    - A trip with no end_date gets one every Monday, for as long as
      debt remains — tracked by last_weekly_reminder_date so same-day
      reruns don't double-send.

    A trip with nothing outstanding (fully settled, or no shared
    expenses at all) is skipped by both paths. Returns how many trips
    were reminded, for the caller to log.
    """
    today = today or datetime.now(UTC).date()
    reminded = 0

    ended_yesterday = db.scalars(
        _trip_query().where(
            Trip.end_date == today - timedelta(days=1),
            Trip.end_date_reminder_sent_at.is_(None),
        )
    ).all()
    for trip in ended_yesterday:
        if _remind_trip_debtors(trip):
            reminded += 1
        trip.end_date_reminder_sent_at = datetime.now(UTC)

    if today.weekday() == 0:  # Monday
        ongoing = db.scalars(
            _trip_query().where(
                Trip.end_date.is_(None),
                or_(
                    Trip.last_weekly_reminder_date.is_(None),
                    Trip.last_weekly_reminder_date < today,
                ),
            )
        ).all()
        for trip in ongoing:
            if _remind_trip_debtors(trip):
                reminded += 1
            trip.last_weekly_reminder_date = today

    db.commit()
    return reminded
