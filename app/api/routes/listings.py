"""Listing routes — POST /listings, GET /listings/{id}, GET /listings/search."""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.broker import Broker
from app.schemas.listing import ListingCreate, ListingResponse
from app.services import listing_service, geo_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Listings"])


# ---------------------------------------------------------------------------
# AI pipeline helpers (graceful when ai/ package is not yet available)
# ---------------------------------------------------------------------------


def _trigger_ai_background_tasks(background_tasks: BackgroundTasks, listing_id: int) -> None:
    """Schedule Person 1's embedding + amenities pipelines as background tasks.

    Wrapped in ``try/except ImportError`` so this endpoint still works during
    isolated development before Person 1's ``ai/`` package physically exists
    alongside this repo.
    """
    try:
        from ai.embeddings.embed_listings import embed_single  # type: ignore[import-untyped]

        background_tasks.add_task(embed_single, listing_id)
        logger.info("Queued embed_single for listing %s", listing_id)
    except ImportError:
        logger.warning(
            "ai.embeddings.embed_listings not available — skipping embed_single "
            "for listing %s (expected during isolated backend development)",
            listing_id,
        )

    try:
        from ai.amenities.amenities_service import fetch_and_cache  # type: ignore[import-untyped]

        background_tasks.add_task(fetch_and_cache, listing_id)
        logger.info("Queued fetch_and_cache for listing %s", listing_id)
    except ImportError:
        logger.warning(
            "ai.amenities.amenities_service not available — skipping fetch_and_cache "
            "for listing %s (expected during isolated backend development)",
            listing_id,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/listings",
    response_model=ListingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a new listing (broker only)",
)
def create_listing(
    body: ListingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ListingResponse:
    """Create a listing, then queue AI embedding + amenities caching.

    Only authenticated brokers may call this endpoint.  The AI background
    tasks (``embed_single`` and ``fetch_and_cache``) are scheduled but not
    awaited — if the ``ai/`` package is missing, a warning is logged and
    the listing is still created successfully.
    """
    if not isinstance(current_user, Broker):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only brokers can create listings",
        )

    listing = listing_service.create_listing(db, broker_id=current_user.id, data=body)

    # Queue Person 1's pipelines — uses embed_single (per-listing),
    # NOT run() which is only for the initial batch pass over seeded data.
    _trigger_ai_background_tasks(background_tasks, listing.id)

    return listing  # type: ignore[return-value]


@router.get(
    "/listings/search",
    response_model=list[ListingResponse],
    summary="Search listings by radius around a point",
)
def search_listings(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(..., gt=0, le=100, description="Search radius in km"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    db: Session = Depends(get_db),
) -> list[ListingResponse]:
    """Return listings within *radius_km* of the given lat/lng."""
    results = geo_service.search_by_radius(db, lat=lat, lng=lng, radius_km=radius_km, limit=limit)
    return results  # type: ignore[return-value]


@router.get(
    "/listings/{listing_id}",
    response_model=ListingResponse,
    summary="Fetch a single listing by ID",
)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
) -> ListingResponse:
    """Return the listing including cached amenities, or 404 if not found."""
    listing = listing_service.get_listing(db, listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with id {listing_id} not found",
        )
    return listing  # type: ignore[return-value]
