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
            [{"currency": "USD", "amount": 10}],
        )
        self.assertEqual(
            dashboard["spending_by_category"],
            [{"category": "food", "currency": "USD", "amount": 10}],
        )
        self.assertEqual(
            dashboard["spending_by_day"],
            [{"date": "2026-07-01", "currency": "USD", "amount": 10}],
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

    def test_dashboard_excludes_other_members_personal_spending(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Dashboard Test", "start_date": "2026-07-01"},
        ).json()
        owner = trip["participants"][0]

        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "member@example.com",
                "password": "secure-password-456",
                "display_name": "Member Person",
            },
        )
        self.assertEqual(register_response.status_code, 201)
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "member@example.com",
                "password": "secure-password-456",
            },
        )
        member_headers = {
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        }

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
        member = accept_response.json()

        # A shared expense both should see.
        self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Dinner",
                "amount": 20,
                "paid_by": owner["id"],
                "split_among": [owner["id"], member["id"]],
                "expense_type": "shared",
                "category": "food",
                "date": "2026-07-01",
                "currency": "USD",
            },
        )
        # The owner's own personal expense.
        self.client.post(
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
        # The member's own personal expense, recorded under their own login.
        self.client.post(
            f"/api/trips/{trip['id']}/expenses",
            json={
                "title": "Souvenir",
                "amount": 15,
                "paid_by": member["id"],
                "split_among": [member["id"]],
                "expense_type": "personal",
                "category": "shopping",
                "date": "2026-07-01",
                "currency": "USD",
            },
            headers=member_headers,
        )

        owner_dashboard = self.client.get(
            f"/api/trips/{trip['id']}/dashboard"
        ).json()
        member_dashboard = self.client.get(
            f"/api/trips/{trip['id']}/dashboard",
            headers=member_headers,
        ).json()

        # Both totals include the $20 shared expense plus only the
        # viewer's own $5 or $15 personal expense — never the other
        # member's hidden personal spending.
        self.assertEqual(
            owner_dashboard["total_trip_spending"],
            [{"currency": "USD", "amount": 25}],
        )
        self.assertEqual(
            member_dashboard["total_trip_spending"],
            [{"currency": "USD", "amount": 35}],
        )

        owner_paid = {
            item["participant_id"]: item["amount"]
            for item in owner_dashboard["paid_by_person"]
        }
        member_paid = {
            item["participant_id"]: item["amount"]
            for item in member_dashboard["paid_by_person"]
        }
        self.assertEqual(owner_paid[member["id"]], 0)
        self.assertEqual(member_paid[owner["id"]], 20)

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