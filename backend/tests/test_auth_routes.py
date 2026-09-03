from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from app.orm_models import RefreshToken, User
from app.security import hash_refresh_token, verify_password
from tests.base import DatabaseTestCase
from app.config import settings


class AuthRouteTests(DatabaseTestCase):
    def test_registers_user_and_hashes_password(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "User@Example.com",
                "password": "secure-password-123",
                "display_name": "Test User",
            },
        )

        self.assertEqual(response.status_code, 201)

        body = response.json()
        self.assertEqual(body["email"], "user@example.com")
        self.assertEqual(body["display_name"], "Test User")
        self.assertNotIn("password", body)
        self.assertNotIn("password_hash", body)

        user = self.session.scalar(
            select(User).where(User.email == "user@example.com")
        )
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, "secure-password-123")
        self.assertTrue(
            verify_password(
                "secure-password-123",
                user.password_hash,
            )
        )

    def test_rejects_duplicate_email_case_insensitively(self) -> None:
        first_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "secure-password-123",
                "display_name": "First User",
            },
        )
        self.assertEqual(first_response.status_code, 201)

        second_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "USER@example.com",
                "password": "another-password-456",
                "display_name": "Second User",
            },
        )

        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(
            second_response.json()["detail"],
            "Email is already registered",
        )

    def test_rejects_short_password(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",
                "display_name": "Test User",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_invalid_email(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "secure-password-123",
                "display_name": "Test User",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_login_returns_valid_access_token(self) -> None:
        registered = self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "secure-password-123",
                "display_name": "Test User",
            },
        )
        self.assertEqual(registered.status_code, 201)

        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "USER@example.com",
                "password": "secure-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token_type"], "bearer")
        self.assertIn("refresh_token", response.json())

        payload = jwt.decode(
            response.json()["access_token"],
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        self.assertEqual(
            payload["sub"],
            registered.json()["id"],
        )
        self.assertIn("exp", payload)

        stored_token = self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash
                == hash_refresh_token(response.json()["refresh_token"])
            )
        )
        self.assertIsNotNone(stored_token)
        self.assertIsNone(stored_token.revoked_at)

    def test_login_rejects_wrong_password(self) -> None:
        self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "secure-password-123",
                "display_name": "Test User",
            },
        )

        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "user@example.com",
                "password": "wrong-password",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Invalid email or password",
        )

    def test_login_rejects_unknown_email(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": "missing@example.com",
                "password": "some-password",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Invalid email or password",
        )

    def test_me_returns_current_user(self) -> None:
        registered = self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "secure-password-123",
                "display_name": "Test User",
            },
        )
        login = self.client.post(
            "/api/auth/login",
            json={
                "email": "user@example.com",
                "password": "secure-password-123",
            },
        )

        response = self.client.get(
            "/api/auth/me",
            headers={
                "Authorization": (
                    f"Bearer {login.json()['access_token']}"
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], registered.json()["id"])
        self.assertEqual(response.json()["email"], "user@example.com")
        self.assertNotIn("password_hash", response.json())

    def test_me_rejects_missing_token(self) -> None:
        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Could not validate credentials",
        )

    def test_me_rejects_invalid_token(self) -> None:
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(response.status_code, 401)

    def test_me_rejects_expired_token(self) -> None:
        expired_token = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000000",
                "exp": 0,
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = self.client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {expired_token}",
            },
        )

        self.assertEqual(response.status_code, 401)

    def _register_and_login(self) -> dict:
        self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "secure-password-123",
                "display_name": "Test User",
            },
        )
        login = self.client.post(
            "/api/auth/login",
            json={
                "email": "user@example.com",
                "password": "secure-password-123",
            },
        )
        return login.json()

    def test_refresh_issues_new_token_pair_and_rotates_old_one(self) -> None:
        tokens = self._register_and_login()

        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        self.assertEqual(response.status_code, 200)
        new_tokens = response.json()
        self.assertNotEqual(
            new_tokens["refresh_token"], tokens["refresh_token"]
        )

        me_response = self.client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {new_tokens['access_token']}"
            },
        )
        self.assertEqual(me_response.status_code, 200)

    def test_refresh_rejects_reused_token(self) -> None:
        tokens = self._register_and_login()

        first = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        self.assertEqual(second.status_code, 401)

    def test_refresh_rejects_unknown_token(self) -> None:
        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": "not-a-real-token"},
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_rejects_expired_token(self) -> None:
        tokens = self._register_and_login()
        stored_token = self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash
                == hash_refresh_token(tokens["refresh_token"])
            )
        )
        stored_token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        self.session.add(stored_token)
        self.session.flush()

        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        self.assertEqual(response.status_code, 401)

    def test_logout_revokes_refresh_token(self) -> None:
        tokens = self._register_and_login()

        logout_response = self.client.post(
            "/api/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        self.assertEqual(logout_response.status_code, 204)

        refresh_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        self.assertEqual(refresh_response.status_code, 401)

    def test_logout_with_unknown_token_is_a_no_op(self) -> None:
        response = self.client.post(
            "/api/auth/logout",
            json={"refresh_token": "not-a-real-token"},
        )

        self.assertEqual(response.status_code, 204)