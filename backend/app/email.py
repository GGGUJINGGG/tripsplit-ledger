import logging

import resend

from app.config import settings


logger = logging.getLogger("app.email")

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


def _send_via_resend(to_email: str, subject: str, html: str) -> None:
    """Send a real email through Resend.

    Only called once a Resend API key is configured. A failure here
    (bad key, Resend outage, rate limit, ...) is logged and swallowed
    rather than raised — the caller has already committed the
    underlying resource (reset token, trip invite) to the database,
    so a flaky email provider shouldn't turn that into a 500 for
    something that actually succeeded.
    """
    try:
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": subject,
                "html": html,
            }
        )
        logger.info("Sent email to %s via Resend: %s", to_email, subject)
    except Exception:
        logger.exception("Failed to send email to %s via Resend", to_email)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    """Send a password-reset email.

    Without a configured Resend API key (RESEND_API_KEY), this is a
    stand-in: it logs the reset link server-side instead of actually
    emailing it. Good enough for local development and a demo without
    a transactional email provider set up; see the README.
    """
    if settings.resend_api_key:
        _send_via_resend(
            to_email,
            "Reset your TripSplit Ledger password",
            "<p>Click the link below to reset your password:</p>"
            f'<p><a href="{reset_url}">{reset_url}</a></p>'
            f"<p>This link expires in "
            f"{settings.password_reset_token_expire_minutes} minutes. "
            "If you did not request this, you can ignore this email.</p>",
        )
        return

    logger.info(
        "Password reset requested for %s — reset link: %s",
        to_email,
        reset_url,
    )


def send_trip_invite_email(to_email: str, trip_name: str, action_url: str) -> None:
    """Send an email inviting someone to join a trip — the invite is
    still pending until they explicitly accept it. `action_url` is a
    registration link if they don't have an account yet, or just the
    app's login page if they do (accepting/declining happens from
    their pending-invitations list once logged in).

    Same Resend-or-log stand-in as send_password_reset_email.
    """
    if settings.resend_api_key:
        _send_via_resend(
            to_email,
            f"You've been invited to join \"{trip_name}\" on TripSplit Ledger",
            f'<p>You\'ve been invited to join the trip "{trip_name}" on '
            "TripSplit Ledger.</p>"
            f'<p><a href="{action_url}">Continue here</a></p>',
        )
        return

    logger.info(
        "Trip invite: %s was invited to join '%s' — continue here: %s",
        to_email,
        trip_name,
        action_url,
    )
