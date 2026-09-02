from tests.base import AuthenticatedDatabaseTestCase


class ExpenseRouteTests(AuthenticatedDatabaseTestCase):

    def test_update_shared_expense_to_personal_persists_type(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Route Test", "start_date": "2026-07-01"},
        ).json()
        alex = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()
        maya = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Maya"},
        ).json()
        expense = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": alex["id"],
                "split_among": [alex["id"], maya["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        ).json()

        updated = self.client.put(
            f"/api/trips/{trip['id']}/expenses/{expense['id']}",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": alex["id"],
                "split_among": [alex["id"], maya["id"]],
                "expense_type": "personal",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )


        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["expense_type"], "personal")
        self.assertEqual(updated.json()["split_among"], [alex["id"]])

        reloaded_trip = self.client.get(f"/api/trips/{trip['id']}").json()
        reloaded_expense = reloaded_trip["expenses"][0]
        self.assertEqual(reloaded_expense["expense_type"], "personal")
        self.assertEqual(reloaded_expense["split_among"], [alex["id"]])

    def test_cannot_access_another_users_expenses(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "expense-owner@example.com",
                "password": "secure-password-456",
                "display_name": "Expense Owner",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "expense-owner@example.com",
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
                "name": "Other User Expense Trip",
                "start_date": "2026-08-01",
            },
        )
        self.assertEqual(trip_response.status_code, 201)

        other_trip = trip_response.json()
        owner = other_trip["participants"][0]

        expense_response = self.client.post(
            f"/api/trips/{other_trip['id']}/expenses",
            headers=other_headers,
            json={
                "title": "Private Expense",
                "amount": 25,
                "paid_by": owner["id"],
                "split_among": [owner["id"]],
                "expense_type": "shared",
                "category": "food",
                "date": "2026-08-01",
                "currency": "USD",
            },
        )
        self.assertEqual(expense_response.status_code, 201)
        expense = expense_response.json()

        list_response = self.client.get(
            f"/api/trips/{other_trip['id']}/expenses"
        )
        self.assertEqual(list_response.status_code, 404)

        get_response = self.client.get(
            f"/api/trips/{other_trip['id']}/expenses/{expense['id']}"
        )
        self.assertEqual(get_response.status_code, 404)

        create_response = self.client.post(
            f"/api/trips/{other_trip['id']}/expenses",
            json={
                "title": "Unauthorized Expense",
                "amount": 10,
                "paid_by": owner["id"],
                "split_among": [owner["id"]],
                "expense_type": "shared",
                "category": "food",
                "date": "2026-08-02",
                "currency": "USD",
            },
        )
        self.assertEqual(create_response.status_code, 404)

        update_response = self.client.put(
            f"/api/trips/{other_trip['id']}/expenses/{expense['id']}",
            json={"title": "Unauthorized Update"},
        )
        self.assertEqual(update_response.status_code, 404)

        delete_response = self.client.delete(
            f"/api/trips/{other_trip['id']}/expenses/{expense['id']}"
        )
        self.assertEqual(delete_response.status_code, 404)

    def test_create_expense_rejects_payer_from_another_trip(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Trip A", "start_date": "2026-07-01"},
        ).json()
        other_trip = self.client.post(
            "/api/trips",
            json={"name": "Trip B", "start_date": "2026-07-01"},
        ).json()
        outsider = self.client.post(
            f"/api/trips/{other_trip['id']}/participants",
            json={"name": "Outsider"},
        ).json()

        response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": outsider["id"],
                "split_among": [outsider["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_create_expense_rejects_split_among_participant_from_another_trip(
        self,
    ) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Trip A", "start_date": "2026-07-01"},
        ).json()
        payer = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()
        other_trip = self.client.post(
            "/api/trips",
            json={"name": "Trip B", "start_date": "2026-07-01"},
        ).json()
        outsider = self.client.post(
            f"/api/trips/{other_trip['id']}/participants",
            json={"name": "Outsider"},
        ).json()

        response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": payer["id"],
                "split_among": [payer["id"], outsider["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_create_expense_rejects_unknown_currency_code(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Currency Test", "start_date": "2026-07-01"},
        ).json()
        alex = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()

        response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": alex["id"],
                "split_among": [alex["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "ABC",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_create_expense_accepts_known_non_usd_currency(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Currency Test", "start_date": "2026-07-01"},
        ).json()
        alex = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()

        response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": alex["id"],
                "split_among": [alex["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "eur",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["currency"], "EUR")

    def test_update_expense_rejects_payer_from_another_trip(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Trip A", "start_date": "2026-07-01"},
        ).json()
        alex = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()
        expense = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": alex["id"],
                "split_among": [alex["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        ).json()
        other_trip = self.client.post(
            "/api/trips",
            json={"name": "Trip B", "start_date": "2026-07-01"},
        ).json()
        outsider = self.client.post(
            f"/api/trips/{other_trip['id']}/participants",
            json={"name": "Outsider"},
        ).json()

        response = self.client.put(
            f"/api/trips/{trip['id']}/expenses/{expense['id']}",
            json={"paid_by": outsider["id"]},
        )

        self.assertEqual(response.status_code, 422)