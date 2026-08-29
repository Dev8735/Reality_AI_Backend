"""Pydantic schemas for Listing data validation and serialization."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class ListingBase(BaseModel):
    """Shared fields across listing create/response schemas."""

    title: str = Field(..., max_length=200, description="Listing headline")
    description: str | None = Field(None, description="Detailed description")
    price: float = Field(..., gt=0, description="Price in INR")
    property_type: Literal["flat", "house_land"] = Field(
        ..., description="Must be 'flat' or 'house_land' per AGENTS.md"
    )
    carpet_area: float | None = Field(None, ge=0)
    built_up_area: float | None = Field(None, ge=0)
    plot_area: float | None = Field(None, ge=0)
    floor_number: int | None = None
    rooms: dict[str, Any] | None = Field(
        None, description="Room breakdown as JSON, e.g. {'bedrooms': 2, 'bathrooms': 1}"
    )


class ListingCreate(ListingBase):
    """Schema for creating a new listing.

    Accepts ``lat`` and ``lng`` as separate floats — the service layer
    converts them into a PostGIS Point on write.  The internal Geometry
    type is never exposed through the API.
    """

    lat: float = Field(..., ge=-90, le=90, description="Latitude (WGS-84)")
    lng: float = Field(..., ge=-180, le=180, description="Longitude (WGS-84)")


class ListingResponse(ListingBase):
    """Schema returned by listing endpoints.

    Includes ``amenities`` per AGENTS.md §3 — may be null until
    Person 1's pipeline populates it.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    broker_id: int
    amenities: dict[str, Any] | None = Field(
        None,
        description=(
            "Cached nearby-amenity data (schools, hospitals, restaurants, "
            "transit, parks) — populated by AI pipeline, may be null"
        ),
    )
    created_at: datetime
