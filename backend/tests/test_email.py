import logging
import unittest
from unittest.mock import patch

from app.config import settings
from app.email import send_password_reset_email, send_trip_invite_email


class EmailTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_key = settings.resend_api_key

    def tearDown(self) -> None:
        settings.resend_api_key = self._original_key

    def test_password_reset_logs_the_link_when_resend_is_not_configured(
        self,
    ) -> None:
        settings.resend_api_key = None

        with self.assertLogs("app.email", level="INFO") as captured:
            send_password_reset_email(
                "user@example.com", "https://example.com/reset?token=abc"
            )

        self.assertTrue(
            any(
                "user@example.com" in message
                and "https://example.com/reset?token=abc" in message
                for message in captured.output
            )
        )

    def test_trip_invite_logs_the_link_when_resend_is_not_configured(
        self,
    ) -> None:
        settings.resend_api_key = None

        with self.assertLogs("app.email", level="INFO") as captured:
            send_trip_invite_email(
                "user@example.com", "Iceland Trip", "https://example.com/"
            )

        self.assertTrue(
            any(
                "user@example.com" in message
                and "Iceland Trip" in message
                and "https://example.com/" in message
                for message in captured.output
            )
        )

    def test_password_reset_calls_resend_when_configured(self) -> None:
        settings.resend_api_key = "re_fake_key_for_testing"

        with patch("app.email.resend.Emails.send") as mock_send:
            send_password_reset_email(
                "user@example.com", "https://example.com/reset?token=abc"
            )

        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args["to"], ["user@example.com"])
        self.assertIn(
            "https://example.com/reset?token=abc", call_args["html"]
        )

    def test_trip_invite_calls_resend_when_configured(self) -> None:
        settings.resend_api_key = "re_fake_key_for_testing"

        with patch("app.email.resend.Emails.send") as mock_send:
            send_trip_invite_email(
                "user@example.com", "Iceland Trip", "https://example.com/"
            )

        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        self.assertEqual(call_args["to"], ["user@example.com"])
        self.assertIn("Iceland Trip", call_args["subject"])
        self.assertIn("https://example.com/", call_args["html"])

    def test_resend_failure_is_logged_and_swallowed_not_raised(self) -> None:
        settings.resend_api_key = "re_fake_key_for_testing"

        with patch(
            "app.email.resend.Emails.send",
            side_effect=RuntimeError("Resend is down"),
        ):
            with self.assertLogs("app.email", level="ERROR") as captured:
                # Must not raise even though the send call blew up.
                send_password_reset_email(
                    "user@example.com", "https://example.com/reset"
                )

        self.assertTrue(
            any("Failed to send email" in message for message in captured.output)
        )
