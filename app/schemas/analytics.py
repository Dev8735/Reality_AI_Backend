"""Pydantic schemas for broker analytics endpoints."""

from pydantic import BaseModel, Field


class ListingAnalyticsItem(BaseModel):
    """Analytics item for a single listing."""

    listing_id: int
    title: str
    lead_count: int = Field(..., description="Number of customer inquiries / leads")


class BrokerAnalyticsResponse(BaseModel):
    """Response payload for GET /brokers/{id}/analytics matching AGENTS.md §3."""

    total_listings: int = Field(..., description="Total active listings owned by this broker")
    total_leads: int = Field(..., description="Total aggregate leads across all listings")
    listings_breakdown: list[ListingAnalyticsItem] = Field(
        default_factory=list,
        description="Per-listing breakdown of views and leads",
    )
