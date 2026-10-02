"""Shared test fixtures and configuration for the Reality AI test suite.

Test isolation strategy: each test runs inside a database transaction that
is rolled back at the end.  This avoids creating a separate test database
while ensuring tests never pollute each other's state.  The approach works
because we override FastAPI's ``get_db`` dependency with a session bound to
the same connection/transaction.

Prerequisite: the Docker Postgres container must be running and Alembic
migrations must have been applied (``alembic upgrade head``).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app


db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    try:
        import psycopg
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    except ImportError:
        pass

engine = create_engine(db_url, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    """Yield a DB session wrapped in a transaction that is always rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Prevent the session from committing — nested calls to commit() become
    # SAVEPOINTs instead, so service-layer commits work normally but the
    # outer transaction is still rolled back at cleanup.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session):
    """FastAPI TestClient with the DB dependency overridden."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifecycle managed by db_session fixture

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_broker(client: TestClient, email: str = "broker@test.com") -> dict:
    """Register a broker and return the response JSON (includes access_token)."""
    resp = client.post("/auth/register", json={
        "email": email,
        "password": "testpass123",
        "name": "Test Broker",
        "role": "broker",
    })
    return resp.json()


def auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}
