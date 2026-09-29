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


class TokenResponse(BaseModel):
    """JWT token returned on successful register or login."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Authenticated user profile returned by GET /auth/me."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Literal["broker", "customer"]
    created_at: datetime
