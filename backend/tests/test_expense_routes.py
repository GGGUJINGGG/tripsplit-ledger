import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class ExpenseRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temp_dir.name) / "trips.json"
        self.data_file.write_text('{"trips": []}', encoding="utf-8")
        self.patch = patch("app.storage.DATA_FILE", self.data_file)
        self.patch.start()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.patch.stop()
        self.temp_dir.cleanup()

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

        settlements = self.client.get(f"/api/trips/{trip['id']}/settlements").json()
        self.assertEqual(settlements["settlements"], [])


if __name__ == "__main__":
    unittest.main()
