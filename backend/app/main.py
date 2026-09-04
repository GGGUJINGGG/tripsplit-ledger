from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import configure_logging
from app.monitoring import configure_sentry
from app.request_logging import RequestLoggingMiddleware
from app.routers import (
    auth,
    dashboard,
    expenses,
    invitations,
    participants,
    settlements,
    trips,
)


configure_logging()
configure_sentry()

app = FastAPI(title="TripSplit Ledger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router, prefix="/api")
app.include_router(trips.router, prefix="/api")
app.include_router(participants.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(settlements.router, prefix="/api")
app.include_router(invitations.router, prefix="/api")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
