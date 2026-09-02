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

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Invitee Person")

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

    def test_invite_rejects_unknown_email(self) -> None:
        trip = self.create_trip()

        response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "nobody@example.com"},
        )

        self.assertEqual(response.status_code, 404)

    def test_invite_rejects_existing_member(self) -> None:
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

    def test_member_cannot_invite_others(self) -> None:
        trip = self.create_trip()
        member_headers = self.register_and_login(
            "member@example.com", "Trip Member"
        )
        self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            json={"email": "member@example.com"},
        )
        self.register_and_login("third-party@example.com", "Third Party")

        response = self.client.post(
            f"/api/trips/{trip['id']}/participants/invite",
            headers=member_headers,
            json={"email": "third-party@example.com"},
        )

        self.assertEqual(response.status_code, 403)