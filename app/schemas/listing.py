"""Pydantic schemas for Listing data validation and serialization."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

try:
    from geoalchemy2.shape import to_shape

    _GEO_AVAILABLE = True
except ImportError:
    _GEO_AVAILABLE = False


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
    ``lat`` / ``lng`` are extracted from the PostGIS ``location`` column.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    broker_id: int
    lat: float | None = Field(None, ge=-90, le=90, description="Latitude (WGS-84)")
    lng: float | None = Field(None, ge=-180, le=180, description="Longitude (WGS-84)")
    amenities: dict[str, Any] | None = Field(
        None,
        description=(
            "Cached nearby-amenity data (schools, hospitals, restaurants, "
            "transit, parks) — populated by AI pipeline, may be null"
        ),
    )
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _extract_coords_from_location(cls, data):  # noqa: N805
        """Extract lat/lng from PostGIS geometry when serialising ORM objects."""
        if not _GEO_AVAILABLE:
            return data

        loc = getattr(data, "location", None)
        if loc is None and isinstance(data, dict):
            loc = data.get("location")

        if loc is not None:
            try:
                point = to_shape(loc)
                if hasattr(data, "__dict__"):
                    # ORM object — set attributes directly
                    object.__setattr__(data, "lat", point.y)
                    object.__setattr__(data, "lng", point.x)
                else:
                    data["lat"] = point.y
                    data["lng"] = point.x
            except Exception:
                pass

        return data
