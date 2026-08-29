"""Tests for polygon boundary search endpoint — POST /listings/search-boundary."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import register_broker, auth_header


# Coordinates forming a polygon around Adajan neighbourhood
ADAJAN_POLYGON = [
    [21.1800, 72.8200],
    [21.1800, 72.8400],
    [21.1600, 72.8400],
    [21.1600, 72.8200],
]


class TestBoundarySearch:
    """POST /listings/search-boundary."""

    def test_boundary_search_valid_polygon(self, client: TestClient):
        # Seed a listing inside Adajan
        token = register_broker(client)["access_token"]
        client.post(
            "/listings",
            json={
                "title": "Flat in Adajan Polygon",
                "price": 5000000,
                "property_type": "flat",
                "lat": 21.1702,
                "lng": 72.8311,
            },
            headers=auth_header(token),
        )

        resp = client.post(
            "/listings/search-boundary",
            json={"polygon": ADAJAN_POLYGON},
        )
        assert resp.status_code == 200
        listings = resp.json()
        assert len(listings) >= 1

    def test_boundary_search_invalid_points_422(self, client: TestClient):
        # Less than 3 points
        resp = client.post(
            "/listings/search-boundary",
            json={"polygon": [[21.1702, 72.8311], [21.1800, 72.8400]]},
        )
        assert resp.status_code == 422
