import unittest

from app.models import Expense, ExpenseCategory, ExpenseType, Participant, Trip
from app.services.calculations import build_dashboard_summary
from app.services.settlements import simplify_settlements


class CalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.alex = Participant(id="alex", name="Alex")
        self.maya = Participant(id="maya", name="Maya")
        self.sam = Participant(id="sam", name="Sam")
        self.trip = Trip(
            id="trip-1",
            name="Test Trip",
            start_date="2026-07-01",
            participants=[self.alex, self.maya, self.sam],
            expenses=[
                Expense(
                    id="expense-1",
                    trip_id="trip-1",
                    title="Hotel",
                    amount=300,
                    paid_by="alex",
                    split_among=["alex", "maya", "sam"],
                    category=ExpenseCategory.HOTEL,
                    date="2026-07-01",
                    currency="USD",
                    created_at="2026-07-01T00:00:00Z",
                    updated_at="2026-07-01T00:00:00Z",
                ),
                Expense(
                    id="expense-2",
                    trip_id="trip-1",
                    title="Dinner",
                    amount=90,
                    paid_by="maya",
                    split_among=["alex", "maya", "sam"],
                    category=ExpenseCategory.FOOD,
                    date="2026-07-01",
                    currency="USD",
                    created_at="2026-07-01T00:00:00Z",
                    updated_at="2026-07-01T00:00:00Z",
                ),
                Expense(
                    id="expense-3",
                    trip_id="trip-1",
                    title="Gas",
                    amount=60,
                    paid_by="sam",
                    split_among=["alex", "sam"],
                    category=ExpenseCategory.GAS,
                    date="2026-07-02",
                    currency="USD",
                    created_at="2026-07-02T00:00:00Z",
                    updated_at="2026-07-02T00:00:00Z",
                ),
                Expense(
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


if __name__ == "__main__":
    unittest.main()
