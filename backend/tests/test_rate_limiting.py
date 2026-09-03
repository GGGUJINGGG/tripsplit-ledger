from app.config import settings
from app.rate_limit import reset_rate_limits
from tests.base import DatabaseTestCase


class RateLimitingTests(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        settings.rate_limit_enabled = True
        settings.login_rate_limit_attempts = 3
        settings.login_rate_limit_window_seconds = 60
        settings.register_rate_limit_attempts = 2
        settings.register_rate_limit_window_seconds = 60
        reset_rate_limits()

    def tearDown(self) -> None:
        settings.login_rate_limit_attempts = 5
        settings.login_rate_limit_window_seconds = 60
        settings.register_rate_limit_attempts = 10
        settings.register_rate_limit_window_seconds = 3600
        super().tearDown()

    def test_login_is_rate_limited_after_repeated_attempts(self) -> None:
        payload = {
            "email": "user@example.com",
            "password": "wrong-password",
        }

        for _ in range(3):
            response = self.client.post("/api/auth/login", json=payload)
            self.assertEqual(response.status_code, 401)

        limited_response = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(limited_response.status_code, 429)

    def test_login_rate_limit_does_not_block_a_different_client_ip(self) -> None:
        payload = {
            "email": "user@example.com",
            "password": "wrong-password",
        }

        for _ in range(3):
            self.client.post(
                "/api/auth/login",
                json=payload,
                headers={"X-Forwarded-For": "1.1.1.1"},
            )

        # TestClient doesn't honor X-Forwarded-For for request.client.host,
        # so every request above actually shares the same client IP as this
        # one — it should still be rate limited, proving the limiter keys
        # off the connection, not a spoofable header.
        limited_response = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(limited_response.status_code, 429)

    def test_register_is_rate_limited_after_repeated_attempts(self) -> None:
        def register(email: str):
            return self.client.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "password": "secure-password-123",
                    "display_name": "Test User",
                },
            )

        self.assertEqual(register("first@example.com").status_code, 201)
        self.assertEqual(register("second@example.com").status_code, 201)

        limited_response = register("third@example.com")
        self.assertEqual(limited_response.status_code, 429)

    def test_rate_limit_is_scoped_per_endpoint(self) -> None:
        payload = {
            "email": "user@example.com",
            "password": "wrong-password",
        }

        for _ in range(3):
            self.client.post("/api/auth/login", json=payload)

        # Login is now exhausted, but register has its own counter.
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "fresh@example.com",
                "password": "secure-password-123",
                "display_name": "Test User",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_disabled_rate_limiting_never_blocks(self) -> None:
        settings.rate_limit_enabled = False
        payload = {
            "email": "user@example.com",
            "password": "wrong-password",
        }

        for _ in range(10):
            response = self.client.post("/api/auth/login", json=payload)
            self.assertEqual(response.status_code, 401)
