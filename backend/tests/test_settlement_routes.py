from tests.base import AuthenticatedDatabaseTestCase


class SettlementRouteTests(AuthenticatedDatabaseTestCase):
    def test_settlements_use_database_expense_shares(
        self,
    ) -> None:
        trip = self.client.post(
            "/api/trips",
            json={
                "name": "Settlement Test",
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

        expense_response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Dinner",
                "amount": 12,
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

        self.assertEqual(
            expense_response.status_code,
            201,
        )

        response = self.client.get(
            f"/api/trips/{trip['id']}/settlements"
        )

        self.assertEqual(response.status_code, 200)

        settlements = response.json()["settlements"]

        self.assertEqual(len(settlements), 2)

        payments = {
            settlement["from_participant_id"]: settlement
            for settlement in settlements
        }

        self.assertEqual(
            set(payments),
            {maya["id"], sam["id"]},
        )

        self.assertEqual(
            payments[maya["id"]]["to_participant_id"],
            alex["id"],
        )
        self.assertEqual(
            payments[sam["id"]]["to_participant_id"],
            alex["id"],
        )

        self.assertEqual(
            payments[maya["id"]]["from_name"],
            "Maya",
        )
        self.assertEqual(
            payments[sam["id"]]["from_name"],
            "Sam",
        )

        self.assertEqual(
            payments[maya["id"]]["to_name"],
            "Alex",
        )
        self.assertEqual(
            payments[sam["id"]]["to_name"],
            "Alex",
        )

        self.assertEqual(
            payments[maya["id"]]["amount"],
            4,
        )
        self.assertEqual(
            payments[sam["id"]]["amount"],
            4,
        )

    def test_cannot_access_another_users_settlements(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "settlement-owner@example.com",
                "password": "secure-password-456",
                "display_name": "Settlement Owner",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "settlement-owner@example.com",
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
                "name": "Private Settlement Trip",
                "start_date": "2026-08-01",
            },
        )
        self.assertEqual(trip_response.status_code, 201)
        other_trip = trip_response.json()

        response = self.client.get(
            f"/api/trips/{other_trip['id']}/settlements"
        )

        self.assertEqual(response.status_code, 404)

    def test_settlements_require_authentication(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={
                "name": "Auth Required Trip",
                "start_date": "2026-07-01",
            },
        ).json()

        self.client.headers.pop("Authorization", None)

        response = self.client.get(
            f"/api/trips/{trip['id']}/settlements"
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Could not validate credentials",
        )