"""Listing persistence service — create, fetch, and filtered search."""

from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement

from app.models.listing import Listing
from app.schemas.listing import ListingCreate


def create_listing(
    db: Session,
    broker_id: int,
    data: ListingCreate,
) -> Listing:
    """Persist a new listing and return the ORM instance.

    Converts ``data.lat`` / ``data.lng`` into a PostGIS Point
    (SRID 4326) — the API never exposes the internal Geometry type.

    This function intentionally does **not** call Person 1's
    embedding or amenities pipelines.  The calling route is
    responsible for scheduling those as FastAPI ``BackgroundTasks``
    so that persistence stays fast and the service stays focused
    on database writes only.
    """
    point = WKTElement(f"POINT({data.lng} {data.lat})", srid=4326)

    listing = Listing(
        broker_id=broker_id,
        title=data.title,
        description=data.description,
        price=data.price,
        property_type=data.property_type,
        location=point,
        carpet_area=data.carpet_area,
        built_up_area=data.built_up_area,
        plot_area=data.plot_area,
        floor_number=data.floor_number,
        rooms=data.rooms,
    )

    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def get_listing(db: Session, listing_id: int) -> Listing | None:
    """Fetch a single listing by its primary key, or ``None`` if missing.

    The route is responsible for turning ``None`` into a 404 response.
    """
    return db.query(Listing).filter(Listing.id == listing_id).first()


def search_listings(
    db: Session,
    filters: dict,
    limit: int = 20,
) -> list[Listing]:
    """Return listings matching the given filters.

    Currently supports:
    - ``price_min`` / ``price_max`` (float)
    - ``property_type`` (``'flat'`` | ``'house_land'``)

    Structured so additional filters can be added later without
    a rewrite.
    """
    query = db.query(Listing)

    if "price_min" in filters and filters["price_min"] is not None:
        query = query.filter(Listing.price >= filters["price_min"])
    if "price_max" in filters and filters["price_max"] is not None:
        query = query.filter(Listing.price <= filters["price_max"])
    if "property_type" in filters and filters["property_type"] is not None:
        query = query.filter(Listing.property_type == filters["property_type"])

    return query.order_by(Listing.created_at.desc()).limit(limit).all()
