"""Authentication API routes."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from vidmation.auth.dependencies import get_current_user, require_active_user
from vidmation.auth.jwt import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from vidmation.auth.password import hash_password, verify_password
from vidmation.auth.rate_limit import check_auth_rate_limit, check_sensitive_rate_limit
from vidmation.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from vidmation.config.settings import get_settings
from vidmation.db.engine import get_session
from vidmation.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_db() -> Session:
    return get_session()


def _hash_token(token: str) -> str:
    """SHA-256 hash a token for safe database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_token_response(user: User, db: Session) -> TokenResponse:
    """Create access + refresh tokens and persist the refresh token hash."""
    settings = get_settings()

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id)

    # Store hashed refresh token on the user record
    user.refresh_token_hash = _hash_token(refresh_token)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
async def signup(body: SignupRequest, request: Request):
    """Register a new user with email and password.

    Returns access and refresh tokens on success.
    """
    check_auth_rate_limit(request)

    db = _get_db()
    try:
        # Check for existing user
        stmt = select(User).where(User.email == body.email.lower())
        existing = db.scalars(stmt).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        user = User(
            email=body.email.lower(),
            password_hash=hash_password(body.password),
            name=body.name,
            is_active=True,
            is_admin=False,
            is_verified=False,
        )
        db.add(user)
        db.flush()  # assign ID before building tokens

        logger.info("New user registered: %s (%s)", user.email, user.id[:8])

        response = _build_token_response(user, db)
        return response

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Signup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account creation failed",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password",
)
async def login(body: LoginRequest, request: Request):
    """Authenticate with email and password.

    Returns access and refresh tokens on success.
    Uses constant-time comparison to prevent timing attacks.
    """
    check_auth_rate_limit(request)

    db = _get_db()
    try:
        stmt = select(User).where(User.email == body.email.lower())
        user = db.scalars(stmt).first()

        # Constant-time: always verify even if user is None to prevent
        # user-enumeration timing attacks.
        if user is None:
            # Hash a dummy password to keep timing consistent
            verify_password(body.password, "$2b$12$" + "x" * 53)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        logger.info("User logged in: %s", user.email)

        response = _build_token_response(user, db)
        return response

    except HTTPException:
        raise
    except Exception:
        logger.exception("Login failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an access token",
)
async def refresh(body: RefreshTokenRequest, request: Request):
    """Exchange a valid refresh token for a new access token pair.

    The old refresh token is invalidated and a new one is issued
    (refresh-token rotation).
    """
    check_auth_rate_limit(request)

    import jwt as pyjwt

    db = _get_db()
    try:
        try:
            payload = decode_token(body.refresh_token)
        except pyjwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )
        except pyjwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if payload.get("type") != TOKEN_TYPE_REFRESH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Verify the refresh token matches the one stored (prevents reuse of old tokens)
        token_hash = _hash_token(body.refresh_token)
        if user.refresh_token_hash != token_hash:
            # Possible token reuse attack — invalidate all sessions
            user.refresh_token_hash = None
            db.commit()
            logger.warning(
                "Refresh token reuse detected for user %s — sessions invalidated",
                user.email,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        response = _build_token_response(user, db)
        return response

    except HTTPException:
        raise
    except Exception:
        logger.exception("Token refresh failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(user: User = Depends(require_active_user)):
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# PUT /auth/me
# ---------------------------------------------------------------------------


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update user profile",
)
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(require_active_user),
):
    """Update the authenticated user's name and/or email."""
    db = _get_db()
    try:
        # Re-attach user to this session
        db_user = db.get(User, user.id)
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if body.email is not None and body.email.lower() != db_user.email:
            # Check uniqueness
            stmt = select(User).where(User.email == body.email.lower())
            existing = db.scalars(stmt).first()
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already in use",
                )
            db_user.email = body.email.lower()
            # Email change should require re-verification in production
            db_user.is_verified = False

        if body.name is not None:
            db_user.name = body.name

        db.commit()
        db.refresh(db_user)

        return UserResponse.model_validate(db_user)

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Profile update failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /auth/change-password
# ---------------------------------------------------------------------------


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(require_active_user),
):
    """Change the authenticated user's password.

    Requires the current password for verification. Invalidates all
    existing refresh tokens.
    """
    db = _get_db()
    try:
        db_user = db.get(User, user.id)
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(body.old_password, db_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        db_user.password_hash = hash_password(body.new_password)
        # Invalidate refresh token — user must log in again on other devices
        db_user.refresh_token_hash = None
        db.commit()

        logger.info("Password changed for user %s", db_user.email)

        return MessageResponse(message="Password changed successfully")

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Password change failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out (invalidate refresh token)",
)
async def logout(user: User = Depends(get_current_user)):
    """Invalidate the user's refresh token.

    The access token remains valid until it expires (stateless),
    but the refresh token can no longer be used to obtain new tokens.
    """
    db = _get_db()
    try:
        db_user = db.get(User, user.id)
        if db_user is not None:
            db_user.refresh_token_hash = None
            db.commit()
            logger.info("User logged out: %s", db_user.email)

        return MessageResponse(message="Logged out successfully")

    except Exception:
        db.rollback()
        logger.exception("Logout failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /auth/forgot-password (stub)
# ---------------------------------------------------------------------------


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset email",
)
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    """Request a password reset email.

    Always returns success to prevent user enumeration.
    Actual email sending will be implemented via Resend.
    """
    check_sensitive_rate_limit(request)

    db = _get_db()
    try:
        stmt = select(User).where(User.email == body.email.lower())
        user = db.scalars(stmt).first()

        if user is not None and user.is_active:
            # Generate a reset token
            raw_token = secrets.token_urlsafe(32)
            user.password_reset_token = _hash_token(raw_token)
            user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.commit()

            # TODO: Send email via Resend
            # from vidmation.notifications.email import send_password_reset_email
            # await send_password_reset_email(
            #     to=user.email,
            #     reset_url=f"https://aividio.com/reset-password?token={raw_token}",
            # )
            logger.info(
                "Password reset requested for %s (token generated, email sending not yet implemented)",
                user.email,
            )

        # Always return success to prevent user enumeration
        return MessageResponse(
            message="If an account with that email exists, a password reset link has been sent"
        )

    except Exception:
        db.rollback()
        logger.exception("Forgot password failed")
        # Still return success to prevent enumeration
        return MessageResponse(
            message="If an account with that email exists, a password reset link has been sent"
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /auth/reset-password (stub)
# ---------------------------------------------------------------------------


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
async def reset_password(body: ResetPasswordRequest, request: Request):
    """Reset a user's password using a reset token from email.

    The token is single-use and expires after 1 hour.
    """
    check_sensitive_rate_limit(request)

    db = _get_db()
    try:
        token_hash = _hash_token(body.token)

        stmt = select(User).where(
            User.password_reset_token == token_hash,
            User.is_active.is_(True),
        )
        user = db.scalars(stmt).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Check expiry
        if (
            user.password_reset_expires_at is None
            or user.password_reset_expires_at < datetime.now(timezone.utc)
        ):
            user.password_reset_token = None
            user.password_reset_expires_at = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired",
            )

        # Update password and clear reset token
        user.password_hash = hash_password(body.new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        # Invalidate refresh tokens
        user.refresh_token_hash = None
        db.commit()

        logger.info("Password reset completed for %s", user.email)

        return MessageResponse(message="Password has been reset successfully")

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Password reset failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )
    finally:
        db.close()
