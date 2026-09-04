from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.email import send_password_reset_email
from app.orm_models import PasswordResetToken, RefreshToken, TripMember, User
from app.rate_limit import enforce_rate_limit
from app.schemas import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_password_reset_token,
    generate_refresh_token,
    hash_password,
    hash_password_reset_token,
    hash_refresh_token,
    password_reset_token_expires_at,
    refresh_token_expires_at,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


def _issue_token_pair(user: User, db: Session) -> TokenResponse:
    raw_refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=refresh_token_expires_at(),
        )
    )
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=raw_refresh_token,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    enforce_rate_limit(
        request,
        scope="register",
        max_attempts=settings.register_rate_limit_attempts,
        window_seconds=settings.register_rate_limit_window_seconds,
    )

    normalized_email = str(payload.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _claim_pending_trip_invitations(db, user)

    return user


def _claim_pending_trip_invitations(db: Session, user: User) -> None:
    """A trip owner can invite someone by email before they have an
    account (see participants.invite_member) — this links every such
    pending placeholder membership to the account the moment someone
    registers with that same email, across every trip they were
    invited to.
    """
    pending_invitations = db.scalars(
        select(TripMember).where(
            TripMember.invited_email == user.email,
            TripMember.user_id.is_(None),
        )
    )
    for member in pending_invitations:
        member.user_id = user.id
        member.display_name = user.display_name
        db.add(member)
    db.commit()

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    enforce_rate_limit(
        request,
        scope="login",
        max_attempts=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )

    normalized_email = str(payload.email).strip().lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None:
        verify_password(
            payload.password,
            DUMMY_PASSWORD_HASH,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _issue_token_pair(user, db)


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_access_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )

    invalid_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if stored_token is None or stored_token.revoked_at is not None:
        raise invalid_token_exception

    if stored_token.expires_at < datetime.now(timezone.utc):
        raise invalid_token_exception

    user = db.get(User, stored_token.user_id)
    if user is None:
        raise invalid_token_exception

    stored_token.revoked_at = datetime.now(timezone.utc)
    db.add(stored_token)

    return _issue_token_pair(user, db)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout_user(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> None:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )

    if stored_token is not None and stored_token.revoked_at is None:
        stored_token.revoked_at = datetime.now(timezone.utc)
        db.add(stored_token)
        db.commit()


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    enforce_rate_limit(
        request,
        scope="forgot-password",
        max_attempts=settings.forgot_password_rate_limit_attempts,
        window_seconds=settings.forgot_password_rate_limit_window_seconds,
    )

    normalized_email = str(payload.email).strip().lower()
    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    # Always respond 202 whether or not the email is registered, so the
    # response can't be used to enumerate which addresses have accounts.
    if user is None:
        return None

    raw_token = generate_password_reset_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_password_reset_token(raw_token),
            expires_at=password_reset_token_expires_at(),
        )
    )
    db.commit()

    reset_url = (
        f"{settings.frontend_base_url.rstrip('/')}"
        f"/reset-password?token={raw_token}"
    )
    send_password_reset_email(user.email, reset_url)
    return None


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    token_hash = hash_password_reset_token(payload.token)
    stored_token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
    )

    invalid_token_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token",
    )

    if stored_token is None or stored_token.used_at is not None:
        raise invalid_token_exception

    if stored_token.expires_at < datetime.now(timezone.utc):
        raise invalid_token_exception

    user = db.get(User, stored_token.user_id)
    if user is None:
        raise invalid_token_exception

    now = datetime.now(timezone.utc)

    user.password_hash = hash_password(payload.new_password)
    stored_token.used_at = now
    db.add(user)
    db.add(stored_token)

    # A password reset should end every other active session too.
    active_refresh_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    for refresh_token in active_refresh_tokens:
        refresh_token.revoked_at = now
        db.add(refresh_token)

    db.commit()


@router.get(
    "/me",
    response_model=UserRead,
)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user