"""Tests for customer chat endpoint — POST /chat."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_header


def register_customer(client: TestClient, email: str = "cust@test.com") -> dict:
    resp = client.post("/auth/register", json={
        "email": email,
        "password": "testpass123",
        "name": "Test Customer",
        "role": "customer",
    })
    return resp.json()


class TestChat:
    """POST /chat."""

    def test_chat_new_conversation(self, client: TestClient):
        token = register_customer(client)["access_token"]
        resp = client.post(
            "/chat",
            json={"message": "Looking for 2BHK flats in Adajan"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert "listings" in data
        assert "[PLACEHOLDER MODE]" in data["reply"]

    def test_chat_unauthenticated_401(self, client: TestClient):
        resp = client.post(
            "/chat",
            json={"message": "Looking for properties"},
        )
        assert resp.status_code == 401
