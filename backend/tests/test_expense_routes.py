from tests.base import AuthenticatedDatabaseTestCase


class ExpenseRouteTests(AuthenticatedDatabaseTestCase):

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

    def test_update_shared_expense_to_personal_persists_type(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Route Test", "start_date": "2026-07-01"},
        ).json()
        owner = trip["participants"][0]
        maya = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Maya"},
        ).json()
        expense = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": owner["id"],
                "split_among": [owner["id"], maya["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        ).json()

        # Personal expenses can only be recorded for yourself, so the
        # payer stays the currently logged-in user (the trip owner).
        updated = self.client.put(
            f"/api/trips/{trip['id']}/expenses/{expense['id']}",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": owner["id"],
                "split_among": [owner["id"], maya["id"]],
                "expense_type": "personal",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )


        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["expense_type"], "personal")
        self.assertEqual(updated.json()["split_among"], [owner["id"]])

        reloaded_trip = self.client.get(f"/api/trips/{trip['id']}").json()
        reloaded_expense = reloaded_trip["expenses"][0]
        self.assertEqual(reloaded_expense["expense_type"], "personal")
        self.assertEqual(reloaded_expense["split_among"], [owner["id"]])

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

    def test_create_personal_expense_rejects_non_self_payer(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Trip A", "start_date": "2026-07-01"},
        ).json()
        alex = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()

        response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Souvenir",
                "amount": 20,
                "paid_by": alex["id"],
                "split_among": [alex["id"]],
                "expense_type": "personal",
                "category": "shopping",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "Personal expenses can only be recorded for yourself",
        )

    def test_create_personal_expense_allows_self_payer(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Trip A", "start_date": "2026-07-01"},
        ).json()
        owner = trip["participants"][0]

        response = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Coffee",
                "amount": 5,
                "paid_by": owner["id"],
                "split_among": [owner["id"]],
                "expense_type": "personal",
                "category": "food",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )

        self.assertEqual(response.status_code, 201)

    def test_update_personal_expense_rejects_non_self_payer(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Trip A", "start_date": "2026-07-01"},
        ).json()
        owner = trip["participants"][0]
        alex = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        ).json()
        expense = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Tickets",
                "amount": 100,
                "paid_by": owner["id"],
                "split_among": [owner["id"], alex["id"]],
                "expense_type": "shared",
                "category": "tickets",
                "date": "2026-07-01",
                "currency": "USD",
            },
        ).json()

        response = self.client.put(
            f"/api/trips/{trip['id']}/expenses/{expense['id']}",
            json={"paid_by": alex["id"], "expense_type": "personal"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "Personal expenses can only be recorded for yourself",
        )

    def test_personal_expense_hidden_from_other_trip_members(self) -> None:
        owner_headers = dict(self.client.headers)
        member_headers = self.register_and_login(
            "member@example.com", "Member Person"
        )

        trip = self.client.post(
            "/api/trips",
            json={"name": "Trip A", "start_date": "2026-07-01"},
        ).json()
        owner = trip["participants"][0]

        invite_response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "member@example.com"},
        )
        self.assertEqual(invite_response.status_code, 201)
        accept_response = self.client.post(
            f"/api/invitations/{invite_response.json()['id']}/accept",
            headers=member_headers,
        )
        self.assertEqual(accept_response.status_code, 200)

        personal_expense = self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Coffee",
                "amount": 5,
                "paid_by": owner["id"],
                "split_among": [owner["id"]],
                "expense_type": "personal",
                "category": "food",
                "date": "2026-07-01",
                "currency": "USD",
            },
        ).json()

        # The owner can see their own personal expense.
        own_list = self.client.get(
            f"/api/trips/{trip['id']}/expenses",
            headers=owner_headers,
        ).json()
        self.assertIn(
            personal_expense["id"],
            [item["id"] for item in own_list["items"]],
        )

        # The invited member cannot see it in the list, the nested trip
        # response, or by requesting it directly by id.
        member_list = self.client.get(
            f"/api/trips/{trip['id']}/expenses",
            headers=member_headers,
        ).json()
        self.assertNotIn(
            personal_expense["id"],
            [item["id"] for item in member_list["items"]],
        )

        member_trip = self.client.get(
            f"/api/trips/{trip['id']}",
            headers=member_headers,
        ).json()
        self.assertNotIn(
            personal_expense["id"],
            [item["id"] for item in member_trip["expenses"]],
        )

        direct_get = self.client.get(
            f"/api/trips/{trip['id']}/expenses/{personal_expense['id']}",
            headers=member_headers,
        )
        self.assertEqual(direct_get.status_code, 404)

        direct_delete = self.client.delete(
            f"/api/trips/{trip['id']}/expenses/{personal_expense['id']}",
            headers=member_headers,
        )
        self.assertEqual(direct_delete.status_code, 404)

    def _create_trip_with_expenses(self, count: int) -> dict:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Pagination Test", "start_date": "2026-07-01"},
        ).json()
        owner = trip["participants"][0]

        for index in range(count):
            response = self.client.post(
                f"/api/trips/{trip['id']}/expenses",
                json={
                    "title": f"Expense {index}",
                    "amount": 10,
                    "paid_by": owner["id"],
                    "split_among": [owner["id"]],
                    "expense_type": "shared",
                    "category": "food",
                    "date": f"2026-07-{index + 1:02d}",
                    "currency": "USD",
                },
            )
            self.assertEqual(response.status_code, 201)

        return trip

    def test_list_expenses_defaults_to_a_50_item_page(self) -> None:
        trip = self._create_trip_with_expenses(3)

        response = self.client.get(f"/api/trips/{trip['id']}/expenses")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["limit"], 50)
        self.assertEqual(body["offset"], 0)
        self.assertEqual(len(body["items"]), 3)

    def test_list_expenses_respects_limit_and_offset(self) -> None:
        trip = self._create_trip_with_expenses(5)

        first_page = self.client.get(
            f"/api/trips/{trip['id']}/expenses?limit=2&offset=0"
        ).json()
        second_page = self.client.get(
            f"/api/trips/{trip['id']}/expenses?limit=2&offset=2"
        ).json()
        third_page = self.client.get(
            f"/api/trips/{trip['id']}/expenses?limit=2&offset=4"
        ).json()

        self.assertEqual(first_page["total"], 5)
        self.assertEqual(len(first_page["items"]), 2)
        self.assertEqual(len(second_page["items"]), 2)
        self.assertEqual(len(third_page["items"]), 1)

        # Newest-first ordering (expense_date desc), so page 1 starts
        # with "Expense 4" (2026-07-05) and pages don't overlap.
        all_titles = [
            item["title"]
            for page in (first_page, second_page, third_page)
            for item in page["items"]
        ]
        self.assertEqual(
            all_titles,
            ["Expense 4", "Expense 3", "Expense 2", "Expense 1", "Expense 0"],
        )
        self.assertEqual(len(set(all_titles)), 5)

    def test_list_expenses_rejects_out_of_range_limit(self) -> None:
        trip = self._create_trip_with_expenses(1)

        too_high = self.client.get(
            f"/api/trips/{trip['id']}/expenses?limit=201"
        )
        too_low = self.client.get(
            f"/api/trips/{trip['id']}/expenses?limit=0"
        )
        negative_offset = self.client.get(
            f"/api/trips/{trip['id']}/expenses?offset=-1"
        )

        self.assertEqual(too_high.status_code, 422)
        self.assertEqual(too_low.status_code, 422)
        self.assertEqual(negative_offset.status_code, 422)

    def test_list_expenses_total_excludes_other_members_personal_expenses(
        self,
    ) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Pagination Privacy Test", "start_date": "2026-07-01"},
        ).json()
        owner = trip["participants"][0]

        member_headers = self.register_and_login(
            "pagination-member@example.com", "Pagination Member"
        )
        invite_response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "pagination-member@example.com"},
        )
        self.assertEqual(invite_response.status_code, 201)
        member_id = invite_response.json()["id"]
        accept_response = self.client.post(
            f"/api/invitations/{member_id}/accept",
            headers=member_headers,
        )
        self.assertEqual(accept_response.status_code, 200)
        member = accept_response.json()

        self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Shared Dinner",
                "amount": 20,
                "paid_by": owner["id"],
                "split_among": [owner["id"], member["id"]],
                "expense_type": "shared",
                "category": "food",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )
        self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            headers=member_headers,
            json={
                "title": "Member's Private Coffee",
                "amount": 5,
                "paid_by": member["id"],
                "split_among": [member["id"]],
                "expense_type": "personal",
                "category": "food",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )

        owner_page = self.client.get(
            f"/api/trips/{trip['id']}/expenses"
        ).json()

        self.assertEqual(owner_page["total"], 1)
        self.assertEqual(
            [item["title"] for item in owner_page["items"]],
            ["Shared Dinner"],
        )