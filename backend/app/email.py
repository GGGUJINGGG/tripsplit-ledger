import logging
from typing import Any

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


def send_settlement_reminder_email(
    to_email: str,
    trip_name: str,
    debts: list[dict[str, Any]],
    trip_url: str,
) -> None:
    """Remind someone what they still owe on a trip. `debts` is that
    person's own outstanding settlements — each a
    {"to_name", "amount", "currency"} dict, as produced by
    app.services.reminders — never anyone else's.

    Same Resend-or-log stand-in as the other transactional emails.
    """
    debt_lines = "".join(
        f"<li>Pay {debt['to_name']}: {debt['currency']} {debt['amount']:.2f}</li>"
        for debt in debts
    )

    if settings.resend_api_key:
        _send_via_resend(
            to_email,
            f'You still owe money on "{trip_name}"',
            f'<p>You still have outstanding balances on "{trip_name}":</p>'
            f"<ul>{debt_lines}</ul>"
            f'<p><a href="{trip_url}">View the trip</a></p>',
        )
        return

    logger.info(
        "Settlement reminder for %s on '%s': %s — view at %s",
        to_email,
        trip_name,
        debts,
        trip_url,
    )


def send_payment_confirmation_request_email(
    to_email: str,
    trip_name: str,
    payer_name: str,
    amount: float,
    currency: str,
    trip_url: str,
) -> None:
    """Tell someone a payment has been recorded as paid to them and is
    waiting on their confirmation before it counts toward anyone's
    balance — see app/services/calculations.py for why pending payments
    are excluded from balance math until then.

    Same Resend-or-log stand-in as the other transactional emails.
    """
    formatted_amount = f"{currency} {amount:.2f}"

    if settings.resend_api_key:
        _send_via_resend(
            to_email,
            f'{payer_name} says they paid you on "{trip_name}"',
            f"<p>{payer_name} recorded a payment of {formatted_amount} to you "
            f'on "{trip_name}". It won\'t count toward anyone\'s balance until '
            "you confirm you actually received it.</p>"
            f'<p><a href="{trip_url}">Review and confirm</a></p>',
        )
        return

    logger.info(
        "Payment confirmation requested: %s says they paid %s to %s on "
        "'%s' — review at %s",
        payer_name,
        formatted_amount,
        to_email,
        trip_name,
        trip_url,
    )
