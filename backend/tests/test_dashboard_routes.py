from tests.base import DatabaseTestCase


class DashboardRouteTests(DatabaseTestCase):
    def test_dashboard_uses_database_expenses_and_shares(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={
                "name": "Dashboard Test",
                "start_date": "2026-07-01",
            },
        ).json()

        alex = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()
        maya = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Maya"},
        ).json()
        sam = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Sam"},
        ).json()

        self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Dinner",
                "amount": 10,
                "paid_by": alex["id"],
                "split_among": [
                    alex["id"],
                    maya["id"],
                    sam["id"],
                ],
                "expense_type": "shared",
                "category": "food",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )

        response = self.client.get(
            f"/api/trips/{trip['id']}/dashboard"
        )

        self.assertEqual(response.status_code, 200)
        dashboard = response.json()

        self.assertEqual(
            dashboard["total_trip_spending"],
            10,
        )
        self.assertEqual(
            dashboard["spending_by_category"],
            [{"category": "food", "amount": 10}],
        )
        self.assertEqual(
            dashboard["spending_by_day"],
            [{"date": "2026-07-01", "amount": 10}],
        )

        paid = {
            item["participant_id"]: item["amount"]
            for item in dashboard["paid_by_person"]
        }
        owed = {
            item["participant_id"]: item["amount"]
            for item in dashboard["owed_by_person"]
        }

        self.assertEqual(paid[alex["id"]], 10)
        self.assertEqual(paid[maya["id"]], 0)
        self.assertEqual(paid[sam["id"]], 0)
        self.assertEqual(
            round(sum(owed.values()), 2),
            10,
        )