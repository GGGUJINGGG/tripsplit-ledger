import sentry_sdk

from app.config import settings


def configure_sentry() -> None:
    """Enable Sentry error monitoring, if a DSN is configured.

    No Sentry project is set up for this app by default — set
    SENTRY_DSN (and optionally SENTRY_ENVIRONMENT) to turn this on.
    With no DSN, this is a no-op: the app runs exactly as it did
    before this existed.
    """
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )
