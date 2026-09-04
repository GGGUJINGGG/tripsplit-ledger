from tests.base import AuthenticatedDatabaseTestCase


class InvitationRouteTests(AuthenticatedDatabaseTestCase):
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

    def create_trip(self, name: str) -> dict:
        response = self.client.post(
            "/api/trips",
            json={"name": name, "start_date": "2026-07-01"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_list_pending_invitations_returns_only_current_users_invites(
        self,
    ) -> None:
        trip = self.create_trip("Trip One")
        invitee_headers = self.register_and_login(
            "invitee@example.com", "Invitee"
        )
        other_headers = self.register_and_login(
            "someone-else@example.com", "Someone Else"
        )

        self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee@example.com"},
        )

        invitee_view = self.client.get(
            "/api/invitations", headers=invitee_headers
        ).json()
        self.assertEqual(len(invitee_view), 1)
        self.assertEqual(invitee_view[0]["trip_name"], "Trip One")

        other_view = self.client.get(
            "/api/invitations", headers=other_headers
        ).json()
        self.assertEqual(other_view, [])

    def test_list_pending_invitations_requires_authentication(self) -> None:
        response = self.client.get(
            "/api/invitations",
            headers={"Authorization": ""},
        )
        self.assertEqual(response.status_code, 401)

    def test_accept_invitation_makes_the_invitee_a_real_member(self) -> None:
        trip = self.create_trip("Trip Two")
        invitee_headers = self.register_and_login(
            "invitee2@example.com", "Invitee Two"
        )
        invitation_id = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee2@example.com"},
        ).json()["id"]

        accept_response = self.client.post(
            f"/api/invitations/{invitation_id}/accept",
            headers=invitee_headers,
        )

        self.assertEqual(accept_response.status_code, 200)
        body = accept_response.json()
        self.assertEqual(body["name"], "Invitee Two")
        self.assertIsNotNone(body["user_id"])

        # No longer pending.
        pending = self.client.get(
            "/api/invitations", headers=invitee_headers
        ).json()
        self.assertEqual(pending, [])

        # Genuinely a member now — can view the trip.
        trip_view = self.client.get(
            f"/api/trips/{trip['id']}", headers=invitee_headers
        )
        self.assertEqual(trip_view.status_code, 200)

    def test_accept_invitation_rejects_a_different_users_invite(self) -> None:
        trip = self.create_trip("Trip Three")
        self.register_and_login("invitee3@example.com", "Invitee Three")
        invitation_id = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee3@example.com"},
        ).json()["id"]

        wrong_headers = self.register_and_login(
            "wrong-person@example.com", "Wrong Person"
        )
        response = self.client.post(
            f"/api/invitations/{invitation_id}/accept",
            headers=wrong_headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_accept_unknown_invitation_returns_404(self) -> None:
        headers = self.register_and_login(
            "nobody-invited@example.com", "Nobody Invited"
        )
        response = self.client.post(
            "/api/invitations/00000000-0000-0000-0000-000000000000/accept",
            headers=headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_accepting_twice_returns_404_the_second_time(self) -> None:
        trip = self.create_trip("Trip Four")
        invitee_headers = self.register_and_login(
            "invitee4@example.com", "Invitee Four"
        )
        invitation_id = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee4@example.com"},
        ).json()["id"]

        first = self.client.post(
            f"/api/invitations/{invitation_id}/accept",
            headers=invitee_headers,
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            f"/api/invitations/{invitation_id}/accept",
            headers=invitee_headers,
        )
        self.assertEqual(second.status_code, 404)

    def test_decline_invitation_removes_the_pending_placeholder(self) -> None:
        trip = self.create_trip("Trip Five")
        invitee_headers = self.register_and_login(
            "invitee5@example.com", "Invitee Five"
        )
        invitation_id = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee5@example.com"},
        ).json()["id"]

        decline_response = self.client.delete(
            f"/api/invitations/{invitation_id}",
            headers=invitee_headers,
        )
        self.assertEqual(decline_response.status_code, 204)

        pending = self.client.get(
            "/api/invitations", headers=invitee_headers
        ).json()
        self.assertEqual(pending, [])

        participants = self.client.get(
            f"/api/trips/{trip['id']}/participants"
        ).json()
        self.assertNotIn(
            "invitee5@example.com", [p["name"] for p in participants]
        )

    def test_decline_invitation_rejects_a_different_users_invite(self) -> None:
        trip = self.create_trip("Trip Six")
        self.register_and_login("invitee6@example.com", "Invitee Six")
        invitation_id = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee6@example.com"},
        ).json()["id"]

        wrong_headers = self.register_and_login(
            "wrong-person-2@example.com", "Wrong Person Two"
        )
        response = self.client.delete(
            f"/api/invitations/{invitation_id}",
            headers=wrong_headers,
        )

        self.assertEqual(response.status_code, 404)
