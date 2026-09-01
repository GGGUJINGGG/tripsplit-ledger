from tests.base import DatabaseTestCase


class SettlementRouteTests(DatabaseTestCase):
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