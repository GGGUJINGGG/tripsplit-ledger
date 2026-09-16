from datetime import date, timedelta

from tests.base import AuthenticatedDatabaseTestCase


class PaymentRouteTests(AuthenticatedDatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.trip = self.client.post(
            "/api/trips",
            json={"name": "Payment Test", "start_date": "2026-07-01"},
        ).json()
        self.owner = self.trip["participants"][0]
        self.maya = self.client.post(
            f"/api/trips/{self.trip['id']}/participants",
            json={"name": "Maya"},
        ).json()

    def create_shared_expense(
        self, amount: float, paid_by: str, currency: str = "USD"
    ) -> dict:
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/expenses",
            json={
                "title": "Hotel",
                "amount": amount,
                "paid_by": paid_by,
                "split_among": [self.owner["id"], self.maya["id"]],
                "expense_type": "shared",
                "category": "hotel",
                "date": "2026-07-01",
                "currency": currency,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_payment(self) -> None:
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
                "note": "Venmo",
            },
        )

        self.assertEqual(response.status_code, 201)
        payment = response.json()
        self.assertEqual(payment["from_participant"], self.maya["id"])
        self.assertEqual(payment["to_participant"], self.owner["id"])
        self.assertEqual(payment["amount"], 25)
        self.assertEqual(payment["currency"], "USD")
        self.assertEqual(payment["note"], "Venmo")

    def test_created_payment_appears_on_the_trip_and_in_list_payments(
        self,
    ) -> None:
        created = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        ).json()

        trip = self.client.get(f"/api/trips/{self.trip['id']}").json()
        self.assertEqual([p["id"] for p in trip["payments"]], [created["id"]])

        listed = self.client.get(
            f"/api/trips/{self.trip['id']}/payments"
        ).json()
        self.assertEqual([p["id"] for p in listed], [created["id"]])

    def test_delete_payment(self) -> None:
        created = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        ).json()

        response = self.client.delete(
            f"/api/trips/{self.trip['id']}/payments/{created['id']}"
        )
        self.assertEqual(response.status_code, 204)

        listed = self.client.get(
            f"/api/trips/{self.trip['id']}/payments"
        ).json()
        self.assertEqual(listed, [])

    def test_rejects_paying_yourself(self) -> None:
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.owner["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_unknown_to_participant(self) -> None:
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": "00000000-0000-0000-0000-000000000000",
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_unknown_from_participant(self) -> None:
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": "00000000-0000-0000-0000-000000000000",
                "to_participant": self.maya["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_a_future_date(self) -> None:
        tomorrow = date.today() + timedelta(days=1)
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": str(tomorrow),
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_accepts_todays_date(self) -> None:
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": str(date.today()),
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_deleting_an_unknown_payment_returns_404(self) -> None:
        response = self.client.delete(
            f"/api/trips/{self.trip['id']}/payments/"
            "00000000-0000-0000-0000-000000000000"
        )
        self.assertEqual(response.status_code, 404)

    def test_rejects_non_positive_amount(self) -> None:
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 0,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_requires_authentication(self) -> None:
        self.client.headers.pop("Authorization", None)

        response = self.client.get(
            f"/api/trips/{self.trip['id']}/payments"
        )
        self.assertEqual(response.status_code, 401)

    def test_recorded_payment_reduces_the_remaining_settlement(self) -> None:
        # Hotel is 100 USD paid by the owner, split evenly, so Maya
        # starts out owing 50.
        self.create_shared_expense(100, self.owner["id"])

        before = self.client.get(
            f"/api/trips/{self.trip['id']}/settlements"
        ).json()["settlements"]
        self.assertEqual(
            [(s["from_participant_id"], s["amount"]) for s in before],
            [(self.maya["id"], 50)],
        )

        # Maya pays the owner back 30 of the 50 mid-trip.
        payment_response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 30,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(payment_response.status_code, 201)

        after = self.client.get(
            f"/api/trips/{self.trip['id']}/settlements"
        ).json()["settlements"]
        self.assertEqual(
            [(s["from_participant_id"], s["amount"]) for s in after],
            [(self.maya["id"], 20)],
        )

    def test_settling_up_exactly_leaves_nothing_to_settle(self) -> None:
        self.create_shared_expense(100, self.owner["id"])

        self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 50,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )

        settlements = self.client.get(
            f"/api/trips/{self.trip['id']}/settlements"
        ).json()["settlements"]
        self.assertEqual(settlements, [])

        dashboard = self.client.get(
            f"/api/trips/{self.trip['id']}/dashboard"
        ).json()
        balances = {
            item["participant_id"]: item["balance"]
            for item in dashboard["net_balances"]
        }
        self.assertEqual(balances[self.maya["id"]], 0)
        self.assertEqual(balances[self.owner["id"]], 0)

    def test_deleting_a_payment_restores_the_settlement(self) -> None:
        self.create_shared_expense(100, self.owner["id"])

        payment = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 50,
                "date": "2026-07-05",
                "currency": "USD",
            },
        ).json()

        self.client.delete(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}"
        )

        settlements = self.client.get(
            f"/api/trips/{self.trip['id']}/settlements"
        ).json()["settlements"]
        self.assertEqual(
            [(s["from_participant_id"], s["amount"]) for s in settlements],
            [(self.maya["id"], 50)],
        )

    def test_cannot_delete_a_participant_with_a_recorded_payment(self) -> None:
        # Sam has no expenses at all, only a payment, so this isolates the
        # new payment-history check from the pre-existing expense checks.
        sam = self.client.post(
            f"/api/trips/{self.trip['id']}/participants",
            json={"name": "Sam"},
        ).json()
        self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": sam["id"],
                "to_participant": self.owner["id"],
                "amount": 20,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )

        response = self.client.delete(
            f"/api/trips/{self.trip['id']}/participants/{sam['id']}"
        )
        self.assertEqual(response.status_code, 409)
