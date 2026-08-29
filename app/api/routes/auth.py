"""Authentication routes — POST /auth/register and POST /auth/login."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.broker import Broker
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services.auth_service import (
    DuplicateEmailError,
    authenticate_user,
    register_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


def _make_subject(user: object) -> str:
    """Build the JWT ``sub`` claim in ``role:id`` format."""
    role = "broker" if isinstance(user, Broker) else "customer"
    return f"{role}:{user.id}"  # type: ignore[attr-defined]


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new broker or customer account",
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Create a new user and return a JWT on success."""
    try:
        user = register_user(
            db,
            email=body.email,
            password=body.password,
            name=body.name,
            role=body.role,
        )
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    token = create_access_token(subject=_make_subject(user))
    logger.info("Registered %s id=%s", body.role, user.id)  # type: ignore[attr-defined]
    return TokenResponse(access_token=token)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT",
)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user via email + password.

    Uses FastAPI's ``OAuth2PasswordRequestForm`` so the Swagger UI
    "Authorize" button works out of the box.
    """
    user = authenticate_user(db, email=form.username, password=form.password)
    if user is None:
        # Generic message — don't reveal whether the email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=_make_subject(user))
    return TokenResponse(access_token=token)
