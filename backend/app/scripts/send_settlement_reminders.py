"""Entrypoint for the daily settlement-reminder job.

Not part of the FastAPI app — the web service has no built-in
scheduler, so this is meant to be run once a day by a separate cron
service (see README's Deployment section for how to set that up on
Railway) pointed at this repo with the start command:

    python -m app.scripts.send_settlement_reminders
"""

import logging

from app.database import SessionLocal
from app.logging_config import configure_logging
from app.services.reminders import send_due_settlement_reminders


def main() -> None:
    configure_logging()
    logger = logging.getLogger("app.scripts.send_settlement_reminders")

    with SessionLocal() as db:
        reminded = send_due_settlement_reminders(db)

    logger.info("Sent settlement reminders for %d trip(s)", reminded)


if __name__ == "__main__":
    main()
