"""Pydantic schemas for polygon boundary search requests."""

from pydantic import BaseModel, Field, field_validator


class BoundarySearchRequest(BaseModel):
    """Payload for POST /listings/search-boundary.

    Polygon is a list of ``[lat, lng]`` coordinate pairs.
    """

    polygon: list[list[float]] = Field(
        ...,
        min_length=3,
        description="List of [lat, lng] coordinates forming a drawn polygon",
    )

    @field_validator("polygon")
    @classmethod
    def validate_and_close_polygon(
        cls, points: list[list[float]]
    ) -> list[list[float]]:
        """Ensure valid coordinates, minimum 3 vertices, and auto-close the ring."""
        if len(points) < 3:
            raise ValueError("Polygon must contain at least 3 points")
        if len(points) > 100:
            raise ValueError("Polygon vertex count exceeds maximum limit of 100 points")

        for idx, pt in enumerate(points):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise ValueError(
                    f"Point at index {idx} must be a 2-element list [lat, lng]"
                )
            lat, lng = pt
            if not (-90 <= lat <= 90):
                raise ValueError(
                    f"Point at index {idx} has invalid latitude {lat} (must be in [-90, 90])"
                )
            if not (-180 <= lng <= 180):
                raise ValueError(
                    f"Point at index {idx} has invalid longitude {lng} (must be in [-180, 180])"
                )

        # Auto-close the polygon ring if the first and last points differ
        first_pt = points[0]
        last_pt = points[-1]
        if first_pt[0] != last_pt[0] or first_pt[1] != last_pt[1]:
            points = list(points) + [list(first_pt)]

        return points
