import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.orm_models import User
from app.rate_limit import reset_rate_limits
from app.security import create_access_token, hash_password


test_engine = create_engine(
    settings.test_database_url,
    pool_pre_ping=True,
)


class DatabaseTestCase(unittest.TestCase):
    connection: Connection
    session: Session
    client: TestClient

    def setUp(self) -> None:
        # Rate limiting is disabled by default so it doesn't interfere
        # with tests that call login/register repeatedly. Tests that
        # target the rate limiter itself flip this on and reset the
        # counters afterward.
        settings.rate_limit_enabled = False
        reset_rate_limits()

        # Force email delivery off regardless of what a developer's
        # local .env has configured — tests must never depend on (or
        # burn through the quota of) a real Resend account. Whatever
        # key is or isn't set locally, the suite always exercises the
        # log-only fallback path; test_email.py covers the Resend path
        # directly with a mocked client.
        settings.resend_api_key = None

        self.connection = test_engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )

        def override_get_db() -> Generator[Session, None, None]:
            yield self.session

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        self.session.close()
        self.transaction.rollback()
        self.connection.close()
        settings.rate_limit_enabled = False
        reset_rate_limits()
        settings.resend_api_key = None


class AuthenticatedDatabaseTestCase(DatabaseTestCase):
    user: User

    def setUp(self) -> None:
        super().setUp()

        self.user = User(
            email="authenticated@example.com",
            password_hash=hash_password("secure-password-123"),
            display_name="Authenticated User",
        )
        self.session.add(self.user)
        self.session.flush()

        token = create_access_token(self.user.id)
        self.client.headers.update(
            {"Authorization": f"Bearer {token}"}
        )