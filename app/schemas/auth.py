"""Pydantic schemas for authentication request/response payloads."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration payload — works for both brokers and customers."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)
    role: Literal["broker", "customer"] = Field(
        ..., description="Account type — determines which table the user is created in"
    )


class AuthUser(BaseModel):
    """User profile data returned within TokenResponse."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: Literal["broker", "customer"]


class TokenResponse(BaseModel):
    """JWT token and authenticated user returned on successful register or login."""

    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class UserResponse(AuthUser):
    """Authenticated user profile returned by GET /auth/me."""

    created_at: datetime
