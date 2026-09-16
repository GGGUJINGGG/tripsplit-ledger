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
        # The owner is a real logged-in account, so this payment can't
        # take effect until they confirm they actually received it.
        self.assertEqual(payment["status"], "pending")

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

        # A pending payment doesn't move the settlement until the owner
        # (its recipient) confirms it.
        confirm_response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments/"
            f"{payment_response.json()['id']}/confirm"
        )
        self.assertEqual(confirm_response.status_code, 200)

        after = self.client.get(
            f"/api/trips/{self.trip['id']}/settlements"
        ).json()["settlements"]
        self.assertEqual(
            [(s["from_participant_id"], s["amount"]) for s in after],
            [(self.maya["id"], 20)],
        )

    def test_settling_up_exactly_leaves_nothing_to_settle(self) -> None:
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
        self.client.post(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}/confirm"
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
        self.client.post(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}/confirm"
        )

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

    def register_and_login(self, email: str, display_name: str) -> dict:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "secure-password-456",
                "display_name": display_name,
            },
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "secure-password-456"},
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def invite_and_accept(self, email: str, invitee_headers: dict) -> dict:
        invite_response = self.client.post(
            f"/api/trips/{self.trip['id']}/participants/invite",
            json={"email": email},
        )
        self.assertEqual(invite_response.status_code, 201)
        invitation_id = invite_response.json()["id"]

        accept_response = self.client.post(
            f"/api/invitations/{invitation_id}/accept",
            headers=invitee_headers,
        )
        self.assertEqual(accept_response.status_code, 200)
        return accept_response.json()

    def test_payment_to_a_placeholder_recipient_is_confirmed_immediately(
        self,
    ) -> None:
        # Maya has no account — nobody could ever log in to confirm a
        # payment made to her, so it must take effect right away, same
        # as before this feature existed.
        self.create_shared_expense(100, self.maya["id"])

        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.owner["id"],
                "to_participant": self.maya["id"],
                "amount": 50,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "confirmed")

        settlements = self.client.get(
            f"/api/trips/{self.trip['id']}/settlements"
        ).json()["settlements"]
        self.assertEqual(settlements, [])

    def test_cannot_record_a_payment_claiming_a_different_registered_member_paid(
        self,
    ) -> None:
        # A registered member's own claim to have paid can only come
        # from them — a third party (even the trip owner) can't put
        # words in their mouth about a transfer they never made.
        other_headers = self.register_and_login(
            "payer@example.com", "Payer"
        )
        payer = self.invite_and_accept("payer@example.com", other_headers)

        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": payer["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_registered_member_can_record_their_own_payment(self) -> None:
        payer_headers = self.register_and_login(
            "payer@example.com", "Payer"
        )
        payer = self.invite_and_accept("payer@example.com", payer_headers)

        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            headers=payer_headers,
            json={
                "from_participant": payer["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_anyone_can_still_record_a_payment_on_behalf_of_a_placeholder_payer(
        self,
    ) -> None:
        # Maya has no account, so she can't self-report — the owner
        # recording it for her must still work exactly as before.
        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_recipient_can_confirm_a_pending_payment(self) -> None:
        self.create_shared_expense(100, self.owner["id"])
        invitee_headers = self.register_and_login(
            "recipient@example.com", "Recipient"
        )
        recipient = self.invite_and_accept(
            "recipient@example.com", invitee_headers
        )

        # Owner pays the newly-joined member back for something unrelated
        # to the shared hotel expense — the point here is just exercising
        # the pending -> confirmed transition, not the settlement math.
        payment = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.owner["id"],
                "to_participant": recipient["id"],
                "amount": 10,
                "date": "2026-07-05",
                "currency": "USD",
            },
        ).json()
        self.assertEqual(payment["status"], "pending")

        confirm_response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}/confirm",
            headers=invitee_headers,
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.json()["status"], "confirmed")

    def test_recipient_can_reject_a_pending_payment(self) -> None:
        self.create_shared_expense(100, self.owner["id"])
        invitee_headers = self.register_and_login(
            "recipient@example.com", "Recipient"
        )
        recipient = self.invite_and_accept(
            "recipient@example.com", invitee_headers
        )

        payment = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.owner["id"],
                "to_participant": recipient["id"],
                "amount": 10,
                "date": "2026-07-05",
                "currency": "USD",
            },
        ).json()

        reject_response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}/reject",
            headers=invitee_headers,
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], "rejected")

        # A rejected payment still shows up in history, just excluded
        # from balances — the recipient never had any other stake in
        # this trip, so a rejected payment must leave them with nothing
        # owed either way (the unrelated Maya-owes-owner hotel debt is
        # untouched and expected to still be there).
        settlements = self.client.get(
            f"/api/trips/{self.trip['id']}/settlements"
        ).json()["settlements"]
        recipient_ids = {
            s["from_participant_id"] for s in settlements
        } | {s["to_participant_id"] for s in settlements}
        self.assertNotIn(recipient["id"], recipient_ids)

    def test_non_recipient_cannot_confirm_a_pending_payment(self) -> None:
        # The payment is to the owner; a different (but real, invited)
        # trip member trying to confirm it on the owner's behalf must be
        # rejected — being a trip member isn't enough, you have to be
        # the recipient.
        payment = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        ).json()

        bystander_headers = self.register_and_login(
            "bystander@example.com", "Bystander"
        )
        self.invite_and_accept("bystander@example.com", bystander_headers)

        response = self.client.post(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}/confirm",
            headers=bystander_headers,
        )
        self.assertEqual(response.status_code, 403)

    def test_confirming_an_already_resolved_payment_returns_409(self) -> None:
        payment = self.client.post(
            f"/api/trips/{self.trip['id']}/payments",
            json={
                "from_participant": self.maya["id"],
                "to_participant": self.owner["id"],
                "amount": 25,
                "date": "2026-07-05",
                "currency": "USD",
            },
        ).json()

        first = self.client.post(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}/confirm"
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            f"/api/trips/{self.trip['id']}/payments/{payment['id']}/confirm"
        )
        self.assertEqual(second.status_code, 409)
