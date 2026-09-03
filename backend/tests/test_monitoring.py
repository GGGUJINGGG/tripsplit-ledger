import unittest
from unittest.mock import patch

from app.config import settings
from app.monitoring import configure_sentry


class MonitoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_dsn = settings.sentry_dsn
        self._original_environment = settings.sentry_environment
        self._original_sample_rate = settings.sentry_traces_sample_rate

    def tearDown(self) -> None:
        settings.sentry_dsn = self._original_dsn
        settings.sentry_environment = self._original_environment
        settings.sentry_traces_sample_rate = self._original_sample_rate

    def test_does_not_initialize_sentry_when_dsn_is_unset(self) -> None:
        settings.sentry_dsn = None

        with patch("app.monitoring.sentry_sdk.init") as mock_init:
            configure_sentry()

        mock_init.assert_not_called()

    def test_initializes_sentry_when_dsn_is_set(self) -> None:
        settings.sentry_dsn = "https://example@o0.ingest.sentry.io/0"
        settings.sentry_environment = "production"
        settings.sentry_traces_sample_rate = 0.1

        with patch("app.monitoring.sentry_sdk.init") as mock_init:
            configure_sentry()

        mock_init.assert_called_once_with(
            dsn="https://example@o0.ingest.sentry.io/0",
            environment="production",
            traces_sample_rate=0.1,
        )
