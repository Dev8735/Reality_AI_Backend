"""Broker analytics service — aggregated views and leads per listing."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.broker import Broker
from app.models.lead import Lead
from app.models.listing import Listing
from app.schemas.analytics import BrokerAnalyticsResponse, ListingAnalyticsItem


def get_broker_analytics(
    db: Session, broker_id: int
) -> BrokerAnalyticsResponse | None:
    """Return aggregated listing and lead analytics for a broker.

    Returns ``None`` if no broker with ``broker_id`` exists.
    """
    broker = db.query(Broker).filter(Broker.id == broker_id).first()
    if not broker:
        return None

    # Fetch all listings for this broker
    listings = db.query(Listing).filter(Listing.broker_id == broker_id).all()
    total_listings = len(listings)

    if total_listings == 0:
        return BrokerAnalyticsResponse(
            total_listings=0,
            total_leads=0,
            listings_breakdown=[],
        )

    listing_ids = [l.id for l in listings]

    # Grouped query counting leads per listing
    lead_counts_query = (
        db.query(Lead.listing_id, func.count(Lead.id).label("cnt"))
        .filter(Lead.listing_id.in_(listing_ids))
        .group_by(Lead.listing_id)
        .all()
    )
    counts_map = {listing_id: cnt for listing_id, cnt in lead_counts_query}

    breakdown: list[ListingAnalyticsItem] = []
    total_leads = 0
    for l in listings:
        cnt = counts_map.get(l.id, 0)
        total_leads += cnt
        breakdown.append(
            ListingAnalyticsItem(
                listing_id=l.id,
                title=l.title,
                lead_count=cnt,
            )
        )

    return BrokerAnalyticsResponse(
        total_listings=total_listings,
        total_leads=total_leads,
        listings_breakdown=breakdown,
    )
