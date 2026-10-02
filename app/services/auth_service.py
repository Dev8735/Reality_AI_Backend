"""Authentication service — registration and login business logic."""

from typing import Literal

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.broker import Broker
from app.models.customer import Customer


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class DuplicateEmailError(Exception):
    """Raised when attempting to register with an email that already exists."""


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def register_user(
    db: Session,
    email: str,
    password: str,
    name: str,
    role: Literal["broker", "customer"],
) -> Broker | Customer:
    """Create a new broker or customer account.

    Parameters
    ----------
    db:
        Active database session.
    email:
        Must be unique across the target role's table.
    password:
        Plain-text; hashed before storage.
    name:
        Display name.
    role:
        ``"broker"`` or ``"customer"`` — determines the target table.

    Returns
    -------
    Broker | Customer
        The newly created ORM instance.

    Raises
    ------
    DuplicateEmailError
        If a row with the same email already exists for the given role.
    """
    # Check both Broker and Customer tables for email collision
    existing_broker = db.query(Broker).filter(Broker.email == email).first()
    existing_customer = db.query(Customer).filter(Customer.email == email).first()
    if existing_broker or existing_customer:
        raise DuplicateEmailError(f"An account with email {email!r} already exists")

    hashed = hash_password(password)

    if role == "broker":
        user = Broker(name=name, email=email, password_hash=hashed)
    else:
        user = Customer(name=name, email=email, password_hash=hashed)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> Broker | Customer | None:
    """Verify credentials and return the user, or ``None`` on failure.

    Security note: we intentionally do NOT distinguish between
    "no such user" and "wrong password" in the return value or in any
    eventual error message — this prevents user-enumeration attacks.
    """
    # Try broker first, then customer
    for model_cls in (Broker, Customer):
        user = db.query(model_cls).filter(model_cls.email == email).first()
        if user is not None:
            # Only Broker has password_hash; Customer auth may differ later
            pw_hash = getattr(user, "password_hash", None)
            if pw_hash and verify_password(password, pw_hash):
                return user
            return None  # found the email but password wrong — don't leak which

    return None  # no user found at all — same return shape
