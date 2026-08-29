"""Pydantic schemas for authentication request/response payloads."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


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
