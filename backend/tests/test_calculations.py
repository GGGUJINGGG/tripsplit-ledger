import unittest
from types import SimpleNamespace

from app.orm_models import ExpenseCategory, ExpenseType
from app.services.calculations import (
    build_dashboard_summary,
    filter_visible_expenses,
    is_expense_visible,
    split_cents_evenly,
)
from app.services.settlements import MixedCurrencyError, simplify_settlements


class CalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alex = SimpleNamespace(id="alex", name="Alex")
        self.maya = SimpleNamespace(id="maya", name="Maya")
        self.sam = SimpleNamespace(id="sam", name="Sam")
        self.trip = SimpleNamespace(
            id="trip-1",
            name="Test Trip",
            start_date="2026-07-01",
            participants=[self.alex, self.maya, self.sam],
            expenses=[
                SimpleNamespace(
                    id="expense-1",
                    trip_id="trip-1",
                    title="Hotel",
                    amount=300,
                    paid_by="alex",
                    split_among=["alex", "maya", "sam"],
                    expense_type=ExpenseType.SHARED,
                    category=ExpenseCategory.HOTEL,
                    date="2026-07-01",
                    currency="USD",
                    created_at="2026-07-01T00:00:00Z",
                    updated_at="2026-07-01T00:00:00Z",
                ),
                SimpleNamespace(
                    id="expense-2",
                    trip_id="trip-1",
                    title="Dinner",
                    amount=90,
                    paid_by="maya",
                    split_among=["alex", "maya", "sam"],
                    expense_type=ExpenseType.SHARED,
                    category=ExpenseCategory.FOOD,
                    date="2026-07-01",
                    currency="USD",
                    created_at="2026-07-01T00:00:00Z",
                    updated_at="2026-07-01T00:00:00Z",
                ),
                SimpleNamespace(
                    id="expense-3",
                    trip_id="trip-1",
                    title="Gas",
                    amount=60,
                    paid_by="sam",
                    split_among=["alex", "sam"],
                    expense_type=ExpenseType.SHARED,
                    category=ExpenseCategory.GAS,
                    date="2026-07-02",
                    currency="USD",
                    created_at="2026-07-02T00:00:00Z",
                    updated_at="2026-07-02T00:00:00Z",
                ),
                SimpleNamespace(
                    id="expense-4",
                    trip_id="trip-1",
                    title="Souvenir",
                    amount=120,
                    paid_by="maya",
                    split_among=["maya"],
                    expense_type=ExpenseType.PERSONAL,
                    category=ExpenseCategory.SHOPPING,
                    date="2026-07-02",
                    currency="USD",
                    created_at="2026-07-02T01:00:00Z",
                    updated_at="2026-07-02T01:00:00Z",
                ),
            ],
            created_at="2026-07-01T00:00:00Z",
            updated_at="2026-07-02T00:00:00Z",
        )

    def test_dashboard_summary(self) -> None:
        dashboard = build_dashboard_summary(self.trip)

        self.assertEqual(dashboard.total_trip_spending, 570)
        self.assertEqual(
            [(item.category, item.amount) for item in dashboard.spending_by_category],
            [
                (ExpenseCategory.HOTEL, 300),
                (ExpenseCategory.SHOPPING, 120),
                (ExpenseCategory.FOOD, 90),
                (ExpenseCategory.GAS, 60),
            ],
        )
        self.assertEqual(
            [(item.date, item.amount) for item in dashboard.spending_by_day],
            [("2026-07-01", 390), ("2026-07-02", 180)],
        )
        self.assertEqual(
            {item.participant_id: item.amount for item in dashboard.paid_by_person},
            {"alex": 300, "maya": 210, "sam": 60},
        )
        self.assertEqual(
            {item.participant_id: item.amount for item in dashboard.owed_by_person},
            {"alex": 160, "maya": 130, "sam": 160},
        )
        self.assertEqual(
            {item.participant_id: item.balance for item in dashboard.net_balances},
            {"alex": 140, "maya": -40, "sam": -100},
        )

    def test_simplified_settlements(self) -> None:
        settlement_summary = simplify_settlements(self.trip)

        self.assertEqual(
            [
                (
                    settlement.from_participant_id,
                    settlement.to_participant_id,
                    settlement.amount,
                )
                for settlement in settlement_summary.settlements
            ],
            [("sam", "alex", 100), ("maya", "alex", 40)],
        )

    def test_settlements_reject_mixed_currency_shared_expenses(self) -> None:
        self.trip.expenses[1].currency = "EUR"

        with self.assertRaises(MixedCurrencyError):
            simplify_settlements(self.trip)


class SplitCentsEvenlyTests(unittest.TestCase):
    def test_one_cent_split_among_multiple_participants(self) -> None:
        shares = split_cents_evenly(1, ["alex", "maya", "sam"])

        self.assertEqual(sum(shares.values()), 1)
        self.assertEqual(
            sorted(shares.values()),
            [0, 0, 1],
        )

    def test_split_result_independent_of_input_order(self) -> None:
        forward = split_cents_evenly(10, ["alex", "maya", "sam"])
        reversed_order = split_cents_evenly(
            10, ["sam", "maya", "alex"]
        )

        self.assertEqual(forward, reversed_order)


class ExpenseVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alex_member = SimpleNamespace(id="alex", user_id="alex-user")
        self.maya_member = SimpleNamespace(id="maya", user_id="maya-user")
        self.guest_member = SimpleNamespace(id="guest", user_id=None)

        self.shared_expense = SimpleNamespace(
            expense_type=ExpenseType.SHARED,
            paid_by=self.alex_member,
        )
        self.alex_personal_expense = SimpleNamespace(
            expense_type=ExpenseType.PERSONAL,
            paid_by=self.alex_member,
        )
        self.guest_personal_expense = SimpleNamespace(
            expense_type=ExpenseType.PERSONAL,
            paid_by=self.guest_member,
        )

    def test_shared_expenses_are_always_visible(self) -> None:
        self.assertTrue(is_expense_visible(self.shared_expense, "alex-user"))
        self.assertTrue(is_expense_visible(self.shared_expense, "maya-user"))

    def test_personal_expense_visible_only_to_its_payer(self) -> None:
        self.assertTrue(
            is_expense_visible(self.alex_personal_expense, "alex-user")
        )
        self.assertFalse(
            is_expense_visible(self.alex_personal_expense, "maya-user")
        )

    def test_guest_owned_personal_expense_is_visible_to_no_one(self) -> None:
        # A guest participant has no user_id, so nobody's current_user_id
        # can ever match it.
        self.assertFalse(
            is_expense_visible(self.guest_personal_expense, "alex-user")
        )
        self.assertFalse(
            is_expense_visible(self.guest_personal_expense, None)
        )

    def test_filter_visible_expenses_keeps_shared_and_own_personal_only(
        self,
    ) -> None:
        trip = SimpleNamespace(
            members=[self.alex_member, self.maya_member],
            expenses=[
                self.shared_expense,
                self.alex_personal_expense,
                self.guest_personal_expense,
            ],
        )

        view = filter_visible_expenses(trip, "alex-user")

        self.assertEqual(
            view.expenses,
            [self.shared_expense, self.alex_personal_expense],
        )
        self.assertEqual(view.members, trip.members)


if __name__ == "__main__":
    unittest.main()
