from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.orm_models import PasswordResetToken, User
from app.security import (
    generate_password_reset_token,
    hash_password_reset_token,
    password_reset_token_expires_at,
    verify_password,
)
from tests.base import DatabaseTestCase


class PasswordResetRouteTests(DatabaseTestCase):
    def _register(self) -> dict:
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "original-password-123",
                "display_name": "Test User",
            },
        )
        return response.json()

    def test_forgot_password_creates_token_for_known_user(self) -> None:
        registered = self._register()

        response = self.client.post(
            "/api/auth/forgot-password",
            json={"email": "USER@example.com"},
        )

        self.assertEqual(response.status_code, 202)

        stored_token = self.session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == registered["id"]
            )
        )
        self.assertIsNotNone(stored_token)
        self.assertIsNone(stored_token.used_at)

    def test_forgot_password_returns_202_for_unknown_email_without_creating_token(
        self,
    ) -> None:
        response = self.client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            self.session.scalar(select(PasswordResetToken)), None
        )

    def _issue_reset_token(self, user_id: str) -> str:
        # The API only "sends" the raw token via the (logged, not
        # emailed) reset link — it never returns it in a response body.
        # Tests issue a token directly the same way the endpoint does,
        # rather than trying to intercept a real email.
        raw_token = generate_password_reset_token()
        self.session.add(
            PasswordResetToken(
                user_id=user_id,
                token_hash=hash_password_reset_token(raw_token),
                expires_at=password_reset_token_expires_at(),
            )
        )
        self.session.flush()
        return raw_token

    def _request_reset_token(self) -> str:
        registered = self._register()
        return self._issue_reset_token(registered["id"])

    def test_reset_password_updates_password_and_consumes_token(self) -> None:
        raw_token = self._request_reset_token()

        response = self.client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "brand-new-password-456",
            },
        )
        self.assertEqual(response.status_code, 204)

        user = self.session.scalar(
            select(User).where(User.email == "user@example.com")
        )
        self.assertTrue(
            verify_password("brand-new-password-456", user.password_hash)
        )
        self.assertFalse(
            verify_password("original-password-123", user.password_hash)
        )

        login_with_new_password = self.client.post(
            "/api/auth/login",
            json={
                "email": "user@example.com",
                "password": "brand-new-password-456",
            },
        )
        self.assertEqual(login_with_new_password.status_code, 200)

        login_with_old_password = self.client.post(
            "/api/auth/login",
            json={
                "email": "user@example.com",
                "password": "original-password-123",
            },
        )
        self.assertEqual(login_with_old_password.status_code, 401)

    def test_reset_password_rejects_reused_token(self) -> None:
        raw_token = self._request_reset_token()

        first = self.client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "brand-new-password-456"},
        )
        self.assertEqual(first.status_code, 204)

        second = self.client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "another-password-789"},
        )
        self.assertEqual(second.status_code, 400)

    def test_reset_password_rejects_unknown_token(self) -> None:
        response = self.client.post(
            "/api/auth/reset-password",
            json={
                "token": "not-a-real-token",
                "new_password": "brand-new-password-456",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_rejects_expired_token(self) -> None:
        raw_token = self._request_reset_token()
        stored_token = self.session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash
                == hash_password_reset_token(raw_token)
            )
        )
        stored_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        self.session.add(stored_token)
        self.session.flush()

        response = self.client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "brand-new-password-456"},
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_rejects_short_new_password(self) -> None:
        raw_token = self._request_reset_token()

        response = self.client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "short"},
        )
        self.assertEqual(response.status_code, 422)

    def test_reset_password_revokes_existing_refresh_tokens(self) -> None:
        registered = self._register()
        login = self.client.post(
            "/api/auth/login",
            json={
                "email": "user@example.com",
                "password": "original-password-123",
            },
        )
        old_refresh_token = login.json()["refresh_token"]

        raw_reset_token = self._issue_reset_token(registered["id"])

        reset_response = self.client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_reset_token,
                "new_password": "brand-new-password-456",
            },
        )
        self.assertEqual(reset_response.status_code, 204)

        refresh_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        self.assertEqual(refresh_response.status_code, 401)
