import logging

logger = logging.getLogger("app.email")


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    """"Send" a password-reset email.

    No transactional email provider (SES, Resend, SendGrid, ...) is
    configured for this project, so this just logs the reset link
    server-side instead of actually emailing it. Good enough for local
    development and a demo; swapping in a real provider here is a
    documented gap, not a hidden one — see the README.
    """
    logger.info(
        "Password reset requested for %s — reset link: %s",
        to_email,
        reset_url,
    )


def send_trip_invite_email(to_email: str, trip_name: str, register_url: str) -> None:
    """"Send" an email inviting someone without an account yet to
    register and join a trip. Same stand-in as
    send_password_reset_email — logged, not actually emailed.
    """
    logger.info(
        "Trip invite: %s was invited to join '%s' — register link: %s",
        to_email,
        trip_name,
        register_url,
    )
