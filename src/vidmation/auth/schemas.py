"""Pydantic request/response schemas for auth endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field("", max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Enforce minimum password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )
        return v


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )
        return v


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="Access token lifetime in seconds"
    )


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    is_admin: bool
    is_verified: bool
    subscription_tier: str
    subscription_expires_at: datetime | None = None
    created_at: datetime
    last_login_at: datetime | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
