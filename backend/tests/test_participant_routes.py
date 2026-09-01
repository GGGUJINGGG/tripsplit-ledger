from tests.base import DatabaseTestCase


class ParticipantRouteTests(DatabaseTestCase):
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
            [participant],
        )

        trip_response = self.client.get(
            f"/api/trips/{trip['id']}"
        )

        self.assertEqual(
            trip_response.json()["participants"],
            [participant],
        )

    def test_delete_participant(self) -> None:
        trip = self.create_trip()
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
        self.assertEqual(list_response.json(),[])

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