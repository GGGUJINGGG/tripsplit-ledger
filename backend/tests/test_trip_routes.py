from tests.base import DatabaseTestCase


class TripRouteTests(DatabaseTestCase):
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