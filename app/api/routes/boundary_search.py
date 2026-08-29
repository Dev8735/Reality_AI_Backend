"""Boundary search route — POST /listings/search-boundary (polygon search)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.boundary import BoundarySearchRequest
from app.schemas.listing import ListingResponse
from app.services import geo_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Listings"])


@router.post(
    "/listings/search-boundary",
    response_model=list[ListingResponse],
    summary="Polygon (hand-drawn) boundary search for listings",
)
def search_boundary(
    body: BoundarySearchRequest,
    db: Session = Depends(get_db),
) -> list[ListingResponse]:
    """Return listings located within the hand-drawn polygon boundary.

    Coordinates must be a list of ``[lat, lng]`` pairs.  Catches invalid or
    self-intersecting shapes and returns a 422 Unprocessable Entity error.
    """
    try:
        listings = geo_service.search_by_boundary(db, polygon=body.polygon)
        return listings  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
