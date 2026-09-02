from tests.base import AuthenticatedDatabaseTestCase


class DashboardRouteTests(AuthenticatedDatabaseTestCase):
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

    def test_cannot_access_another_users_dashboard(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "dashboard-owner@example.com",
                "password": "secure-password-456",
                "display_name": "Dashboard Owner",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "dashboard-owner@example.com",
                "password": "secure-password-456",
            },
        )
        self.assertEqual(login_response.status_code, 200)

        other_token = login_response.json()["access_token"]
        other_headers = {
            "Authorization": f"Bearer {other_token}"
        }

        trip_response = self.client.post(
            "/api/trips",
            headers=other_headers,
            json={
                "name": "Private Dashboard Trip",
                "start_date": "2026-08-01",
            },
        )
        self.assertEqual(trip_response.status_code, 201)
        other_trip = trip_response.json()

        response = self.client.get(
            f"/api/trips/{other_trip['id']}/dashboard"
        )

        self.assertEqual(response.status_code, 404)