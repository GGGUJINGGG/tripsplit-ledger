import unittest
from unittest.mock import MagicMock, patch

from app.scripts.send_settlement_reminders import main


class SendSettlementRemindersScriptTests(unittest.TestCase):
    def test_main_opens_a_session_runs_reminders_and_logs_the_count(self) -> None:
        fake_session = MagicMock()
        fake_session.__enter__.return_value = fake_session
        fake_session.__exit__.return_value = False

        with (
            patch(
                "app.scripts.send_settlement_reminders.SessionLocal",
                return_value=fake_session,
            ),
            patch(
                "app.scripts.send_settlement_reminders.send_due_settlement_reminders",
                return_value=3,
            ) as mock_send_due,
            self.assertLogs(
                "app.scripts.send_settlement_reminders", level="INFO"
            ) as captured,
        ):
            main()

        mock_send_due.assert_called_once_with(fake_session)
        self.assertTrue(any("3" in message for message in captured.output))
