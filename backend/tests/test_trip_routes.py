from app.orm_models import MemberRole, TripMember, User
from app.security import create_access_token, hash_password
from tests.base import AuthenticatedDatabaseTestCase


class TripRouteTests(AuthenticatedDatabaseTestCase):
    def add_member(self, trip_id: str) -> dict:
        member_user = User(
            email="member@example.com",
            password_hash=hash_password("secure-password-789"),
            display_name="Trip Member",
        )
        self.session.add(member_user)
        self.session.flush()

        self.session.add(
            TripMember(
                trip_id=trip_id,
                user_id=member_user.id,
                display_name=member_user.display_name,
                role=MemberRole.MEMBER,
            )
        )
        self.session.flush()

        token = create_access_token(member_user.id)
        return {"Authorization": f"Bearer {token}"}

    def assert_validation_message_contains(self, response, expected: str) -> None:
        messages = [error["msg"] for error in response.json()["detail"]]
        self.assertTrue(
            any(expected in message for message in messages),
            f"Expected {expected!r} in validation messages: {messages}",
        )

    def test_accepts_valid_trip_dates(self) -> None:
        response = self.client.post(
            "/api/trips",
            json={
                "name": "Summer Trip",
                "start_date": "2026-07-01",
                "end_date": "2026-07-10",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["start_date"], "2026-07-01")
        self.assertEqual(response.json()["end_date"], "2026-07-10")

    def test_rejects_invalid_trip_date_format(self) -> None:
        for invalid_date in ("2026-99-99", "2026-02-31"):
            with self.subTest(invalid_date=invalid_date):
                response = self.client.post(
                    "/api/trips",
                    json={"name": "Bad Date Trip", "start_date": invalid_date},
                )

                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["detail"][0]["loc"], ["body", "start_date"])
                self.assert_validation_message_contains(response, "valid date")

    def test_rejects_end_date_before_start_date(self) -> None:
        response = self.client.post(
            "/api/trips",
            json={
                "name": "Backwards Trip",
                "start_date": "2026-07-10",
                "end_date": "2026-07-01",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assert_validation_message_contains(response, "end_date cannot be before start_date")

    def test_update_converts_dates_to_storage_strings(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Route Test", "start_date": "2026-07-01"},
        ).json()

        response = self.client.put(
            f"/api/trips/{trip['id']}",
            json={"start_date": "2026-08-01", "end_date": "2026-08-05"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["start_date"], "2026-08-01")
        self.assertEqual(response.json()["end_date"], "2026-08-05")

    def test_update_rejects_end_date_before_existing_start_date(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Route Test", "start_date": "2026-07-10"},
        ).json()

        response = self.client.put(
            f"/api/trips/{trip['id']}",
            json={"end_date": "2026-07-01"},
        )

        self.assertEqual(response.status_code, 422)
        self.assert_validation_message_contains(response, "end_date cannot be before start_date")

    def test_member_cannot_update_trip(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Role Test", "start_date": "2026-07-01"},
        ).json()
        member_headers = self.add_member(trip["id"])

        response = self.client.put(
            f"/api/trips/{trip['id']}",
            headers=member_headers,
            json={"name": "Renamed by member"},
        )

        self.assertEqual(response.status_code, 403)

    def test_member_cannot_delete_trip(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Role Test", "start_date": "2026-07-01"},
        ).json()
        member_headers = self.add_member(trip["id"])

        response = self.client.delete(
            f"/api/trips/{trip['id']}",
            headers=member_headers,
        )

        self.assertEqual(response.status_code, 403)

        still_there = self.client.get(f"/api/trips/{trip['id']}")
        self.assertEqual(still_there.status_code, 200)

    def test_owner_can_update_and_delete_trip(self) -> None:
        trip = self.client.post(
            "/api/trips",
            json={"name": "Role Test", "start_date": "2026-07-01"},
        ).json()
        self.add_member(trip["id"])

        update_response = self.client.put(
            f"/api/trips/{trip['id']}",
            json={"name": "Renamed by owner"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["name"], "Renamed by owner"
        )

        delete_response = self.client.delete(
            f"/api/trips/{trip['id']}"
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_requires_authentication(self) -> None:
        self.client.headers.pop("Authorization", None)

        response = self.client.get("/api/trips")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Could not validate credentials",
        )

    def test_lists_only_current_users_trips(self) -> None:
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "other@example.com",
                "password": "secure-password-456",
                "display_name": "Other User",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "other@example.com",
                "password": "secure-password-456",
            },
        )
        self.assertEqual(login_response.status_code, 200)

        other_token = login_response.json()["access_token"]
        other_trip_response = self.client.post(
            "/api/trips",
            headers={"Authorization": f"Bearer {other_token}"},
            json={
                "name": "Other User Trip",
                "start_date": "2026-08-01",
            },
        )
        self.assertEqual(other_trip_response.status_code, 201)

        other_trip_id = other_trip_response.json()["id"]

        get_response = self.client.get(
            f"/api/trips/{other_trip_id}"
        )
        self.assertEqual(get_response.status_code, 404)

        update_response = self.client.put(
            f"/api/trips/{other_trip_id}",
            json={"name": "Unauthorized Update"},
        )
        self.assertEqual(update_response.status_code, 404)

        delete_response = self.client.delete(
            f"/api/trips/{other_trip_id}"
        )
        self.assertEqual(delete_response.status_code, 404)

        owner_get_response = self.client.get(
            f"/api/trips/{other_trip_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(owner_get_response.status_code, 200)
        self.assertEqual(
            owner_get_response.json()["name"],
            "Other User Trip",
        )

        own_trip_response = self.client.post(
            "/api/trips",
            json={
                "name": "Current User Trip",
                "start_date": "2026-09-01",
            },
        )
        self.assertEqual(own_trip_response.status_code, 201)

        response = self.client.get("/api/trips")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [trip["name"] for trip in response.json()],
            ["Current User Trip"],
        )