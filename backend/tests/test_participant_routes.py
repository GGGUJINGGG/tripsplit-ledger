from tests.base import AuthenticatedDatabaseTestCase


class ParticipantRouteTests(AuthenticatedDatabaseTestCase):
    def register_and_login(
        self,
        email: str,
        display_name: str,
    ) -> dict:
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
            json={
                "email": email,
                "password": "secure-password-456",
            },
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def create_trip(self) -> dict:
        response = self.client.post(
            "/api/trips",
            json={
                "name": "Participant Test",
                "start_date": "2026-07-01",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def invite_and_accept(
        self, trip_id: str, email: str, invitee_headers: dict
    ) -> dict:
        """Invite a registered user and have them accept immediately —
        the setup most tests actually want when they need a real
        (not just pending) trip member.
        """
        invite_response = self.client.post(
            f"/api/trips/{trip_id}/participants/invite",
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

    def test_create_and_list_participants(self) -> None:
        trip = self.create_trip()
        owner = trip["participants"][0]

        create_response = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Alex"},
        )

        self.assertEqual(create_response.status_code, 201)
        participant = create_response.json()
        self.assertEqual(participant["name"], "Alex")

        list_response = self.client.get(
            f"/api/trips/{trip['id']}/participants"
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            list_response.json(),
            [owner, participant],
        )

        trip_response = self.client.get(
            f"/api/trips/{trip['id']}"
        )

        self.assertEqual(
            trip_response.json()["participants"],
            [owner, participant],
        )

    def test_delete_participant(self) -> None:
        trip = self.create_trip()
        owner = trip["participants"][0]
        participant = self.client.post(
            f"/api/trips/{trip['id']}/participants",
            json={"name": "Maya"},
        ).json()

        delete_response = self.client.delete(
            f"/api/trips/{trip['id']}/participants/{participant['id']}"
        )

        self.assertEqual(delete_response.status_code, 204)

        list_response = self.client.get(
            f"/api/trips/{trip['id']}/participants"
        )
        self.assertEqual(list_response.json(), [owner])

    def test_cannot_delete_trip_owner(self) -> None:
        trip = self.create_trip()
        owner = trip["participants"][0]

        response = self.client.delete(
            f"/api/trips/{trip['id']}/participants/{owner['id']}"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Trip owner cannot be deleted",
        )

    def test_cannot_access_participant_through_another_trip(self) -> None:
        first_trip = self.create_trip()
        second_trip = self.create_trip()

        participant = self.client.post(
            f"/api/trips/{first_trip['id']}/participants",
            json={"name": "Sam"},
        ).json()

        response = self.client.delete(
            f"/api/trips/{second_trip['id']}/participants/{participant['id']}"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Participant not found",
        )

    def test_cannot_access_another_users_participants(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "participant-owner@example.com",
                "password": "secure-password-456",
                "display_name": "Participant Owner",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "participant-owner@example.com",
                "password": "secure-password-456",
            },
        )
        self.assertEqual(login_response.status_code, 200)
        other_token = login_response.json()["access_token"]

        trip_response = self.client.post(
            "/api/trips",
            headers={"Authorization": f"Bearer {other_token}"},
            json={
                "name": "Other User Participant Trip",
                "start_date": "2026-08-01",
            },
        )
        self.assertEqual(trip_response.status_code, 201)

        other_trip = trip_response.json()
        owner = other_trip["participants"][0]

        list_response = self.client.get(
            f"/api/trips/{other_trip['id']}/participants"
        )
        self.assertEqual(list_response.status_code, 404)

        create_response = self.client.post(
            f"/api/trips/{other_trip['id']}/participants",
            json={"name": "Unauthorized Participant"},
        )
        self.assertEqual(create_response.status_code, 404)

        delete_response = self.client.delete(
            f"/api/trips/{other_trip['id']}/participants/{owner['id']}"
        )
        self.assertEqual(delete_response.status_code, 404)

        owner_response = self.client.get(
            f"/api/trips/{other_trip['id']}/participants",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response.json(), [owner])

    def test_owner_can_invite_registered_user(self) -> None:
        trip = self.create_trip()
        invitee_headers = self.register_and_login(
            "invitee@example.com", "Invitee Person"
        )

        response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee@example.com"},
        )

        # Inviting a registered user creates a pending placeholder too —
        # they aren't a real member (and can't see the trip) until they
        # explicitly accept.
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["user_id"])
        self.assertEqual(response.json()["name"], "invitee@example.com")
        invitation_id = response.json()["id"]

        pre_accept_view = self.client.get(
            f"/api/trips/{trip['id']}",
            headers=invitee_headers,
        )
        self.assertEqual(pre_accept_view.status_code, 404)

        pending = self.client.get(
            "/api/invitations",
            headers=invitee_headers,
        ).json()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["trip_id"], trip["id"])
        self.assertEqual(pending[0]["trip_name"], trip["name"])

        accept_response = self.client.post(
            f"/api/invitations/{invitation_id}/accept",
            headers=invitee_headers,
        )
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["name"], "Invitee Person")

        trip_response = self.client.get(
            f"/api/trips/{trip['id']}/participants"
        )
        names = {p["name"] for p in trip_response.json()}
        self.assertIn("Invitee Person", names)

        invitee_view = self.client.get(
            f"/api/trips/{trip['id']}",
            headers=invitee_headers,
        )
        self.assertEqual(invitee_view.status_code, 200)

    def test_invite_of_unregistered_email_creates_pending_placeholder(self) -> None:
        trip = self.create_trip()

        response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "Nobody@Example.com"},
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIsNone(body["user_id"])
        self.assertEqual(body["name"], "nobody@example.com")
        self.assertEqual(body["role"], "member")

        participants = self.client.get(
            f"/api/trips/{trip['id']}/participants"
        ).json()
        self.assertIn(
            "nobody@example.com", [p["name"] for p in participants]
        )

    def test_invite_of_unregistered_email_rejects_duplicate_invite(self) -> None:
        trip = self.create_trip()

        first = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "nobody@example.com"},
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "nobody@example.com"},
        )
        self.assertEqual(second.status_code, 409)

    def test_non_owner_cannot_invite_unregistered_email(self) -> None:
        trip = self.create_trip()
        member_headers = self.register_and_login(
            "member@example.com", "Member"
        )
        self.invite_and_accept(trip["id"], "member@example.com", member_headers)

        response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            headers=member_headers,
            json={"email": "nobody@example.com"},
        )

        self.assertEqual(response.status_code, 403)

    def test_invite_of_registered_email_rejects_duplicate_pending_invite(
        self,
    ) -> None:
        trip = self.create_trip()
        self.register_and_login("invitee@example.com", "Invitee Person")

        first_response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee@example.com"},
        )
        self.assertEqual(first_response.status_code, 201)

        second_response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee@example.com"},
        )
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(
            second_response.json()["detail"],
            "This email has already been invited to this trip",
        )

    def test_invite_rejects_already_accepted_member(self) -> None:
        trip = self.create_trip()
        invitee_headers = self.register_and_login(
            "invitee@example.com", "Invitee Person"
        )
        self.invite_and_accept(
            trip["id"], "invitee@example.com", invitee_headers
        )

        response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "invitee@example.com"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "User is already a member of this trip",
        )

    def test_member_cannot_invite_others(self) -> None:
        trip = self.create_trip()
        member_headers = self.register_and_login(
            "member@example.com", "Trip Member"
        )
        self.invite_and_accept(trip["id"], "member@example.com", member_headers)
        self.register_and_login("third-party@example.com", "Third Party")

        response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            headers=member_headers,
            json={"email": "third-party@example.com"},
        )

        self.assertEqual(response.status_code, 403)