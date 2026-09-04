from datetime import date, timedelta
from unittest.mock import patch

from app.orm_models import MemberRole, TripMember, User
from app.security import hash_password
from app.services.reminders import send_due_settlement_reminders
from tests.base import AuthenticatedDatabaseTestCase


class ReminderTests(AuthenticatedDatabaseTestCase):
    def create_trip(self, **overrides) -> dict:
        payload = {"name": "Iceland Trip", "start_date": "2026-08-01"}
        payload.update(overrides)
        response = self.client.post("/api/trips", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def add_registered_member(
        self, trip_id: str, email: str, display_name: str
    ) -> TripMember:
        user = User(
            email=email,
            password_hash=hash_password("secure-password-123"),
            display_name=display_name,
        )
        self.session.add(user)
        self.session.flush()

        member = TripMember(
            trip_id=trip_id,
            user_id=user.id,
            display_name=display_name,
            role=MemberRole.MEMBER,
        )
        self.session.add(member)
        self.session.flush()
        self.session.commit()
        return member

    def add_expense(self, trip: dict, payer_id: str, split_among: list[str]) -> None:
        response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Hotel",
                "amount": 100,
                "paid_by": payer_id,
                "split_among": split_among,
                "expense_type": "shared",
                "category": "hotel",
                "date": trip["start_date"],
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_sends_reminder_the_day_after_an_ended_trip_with_debt(self) -> None:
        yesterday = date(2026, 8, 10)
        today = yesterday + timedelta(days=1)
        trip = self.create_trip(
            start_date="2026-08-01", end_date=str(yesterday)
        )
        owner_id = trip["participants"][0]["id"]
        maya = self.add_registered_member(trip["id"], "maya@example.com", "Maya")
        self.add_expense(trip, owner_id, [owner_id, str(maya.id)])

        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            reminded = send_due_settlement_reminders(self.session, today=today)

        self.assertEqual(reminded, 1)
        mock_send.assert_called_once()
        to_email, trip_name, debts, trip_url = mock_send.call_args[0]
        self.assertEqual(to_email, "maya@example.com")
        self.assertEqual(trip_name, "Iceland Trip")
        self.assertEqual(
            debts,
            [{"to_name": "Authenticated User", "amount": 50.0, "currency": "USD"}],
        )
        self.assertIn(trip["id"], trip_url)

    def test_does_not_send_when_the_ended_trip_is_already_settled(self) -> None:
        yesterday = date(2026, 8, 10)
        today = yesterday + timedelta(days=1)
        trip = self.create_trip(
            start_date="2026-08-01", end_date=str(yesterday)
        )
        # No expenses at all — nothing owed, nothing to remind about.

        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            reminded = send_due_settlement_reminders(self.session, today=today)

        self.assertEqual(reminded, 0)
        mock_send.assert_not_called()

    def test_does_not_resend_the_end_date_reminder_twice(self) -> None:
        yesterday = date(2026, 8, 10)
        today = yesterday + timedelta(days=1)
        trip = self.create_trip(
            start_date="2026-08-01", end_date=str(yesterday)
        )
        owner_id = trip["participants"][0]["id"]
        maya = self.add_registered_member(trip["id"], "maya@example.com", "Maya")
        self.add_expense(trip, owner_id, [owner_id, str(maya.id)])

        with patch("app.services.reminders.send_settlement_reminder_email"):
            first = send_due_settlement_reminders(self.session, today=today)

        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            second = send_due_settlement_reminders(self.session, today=today)

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        mock_send.assert_not_called()

    def test_skips_an_unregistered_guest_but_still_emails_a_registered_debtor(
        self,
    ) -> None:
        yesterday = date(2026, 8, 10)
        today = yesterday + timedelta(days=1)
        trip = self.create_trip(
            start_date="2026-08-01", end_date=str(yesterday)
        )
        owner_id = trip["participants"][0]["id"]
        maya = self.add_registered_member(trip["id"], "maya@example.com", "Maya")
        guest = self.client.post(
            f"/api/trips/{trip['id']}/participants", json={"name": "Guest Sam"}
        ).json()
        self.add_expense(
            trip, owner_id, [owner_id, str(maya.id), guest["id"]]
        )

        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            reminded = send_due_settlement_reminders(self.session, today=today)

        # The trip counts as reminded (there was debt), but only the
        # registered debtor actually receives an email.
        self.assertEqual(reminded, 1)
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args[0][0], "maya@example.com")

    def test_undated_trip_gets_a_weekly_reminder_only_on_monday(self) -> None:
        trip = self.create_trip(start_date="2026-08-01")
        owner_id = trip["participants"][0]["id"]
        maya = self.add_registered_member(trip["id"], "maya@example.com", "Maya")
        self.add_expense(trip, owner_id, [owner_id, str(maya.id)])

        tuesday = date(2026, 8, 11)
        self.assertEqual(tuesday.weekday(), 1)
        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            reminded = send_due_settlement_reminders(self.session, today=tuesday)
        self.assertEqual(reminded, 0)
        mock_send.assert_not_called()

        monday = date(2026, 8, 10)
        self.assertEqual(monday.weekday(), 0)
        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            reminded = send_due_settlement_reminders(self.session, today=monday)
        self.assertEqual(reminded, 1)
        mock_send.assert_called_once()

    def test_undated_trip_does_not_get_two_reminders_the_same_monday(self) -> None:
        trip = self.create_trip(start_date="2026-08-01")
        owner_id = trip["participants"][0]["id"]
        maya = self.add_registered_member(trip["id"], "maya@example.com", "Maya")
        self.add_expense(trip, owner_id, [owner_id, str(maya.id)])
        monday = date(2026, 8, 10)

        with patch("app.services.reminders.send_settlement_reminder_email"):
            first = send_due_settlement_reminders(self.session, today=monday)

        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            second = send_due_settlement_reminders(self.session, today=monday)

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        mock_send.assert_not_called()

        next_monday = monday + timedelta(days=7)
        with patch(
            "app.services.reminders.send_settlement_reminder_email"
        ) as mock_send:
            third = send_due_settlement_reminders(self.session, today=next_monday)
        self.assertEqual(third, 1)
        mock_send.assert_called_once()
