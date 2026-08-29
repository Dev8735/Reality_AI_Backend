"""Listing ORM model — cross-team contract defined in AGENTS.md §4.

Do NOT rename columns, change types, or add/remove fields without
coordinating with the AI and Frontend tracks first.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class Listing(Base):
    """A real-estate listing published by a broker.

    Location is stored as a PostGIS Point (SRID 4326) for geospatial queries.
    The ``embedding`` column is populated by Person 1's AI pipeline
    (``ai.embeddings.embed_listings``), not by this repo.
    The ``amenities`` column is populated by Person 1's amenities service
    (``ai.amenities.amenities_service.fetch_and_cache``), not by this repo.

    If a future PATCH endpoint ever allows editing a listing's location,
    that path must call ``fetch_and_cache(listing.id, force=True)`` afterward
    so amenities data doesn't go stale.
    """

    __tablename__ = "listing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    broker_id = Column(
        Integer, ForeignKey("broker.id"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False)
    property_type = Column(String, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    carpet_area = Column(Numeric, nullable=True)
    built_up_area = Column(Numeric, nullable=True)
    plot_area = Column(Numeric, nullable=True)
    floor_number = Column(Integer, nullable=True)
    rooms = Column(JSON, nullable=True)
    # TODO: CONFIRM embedding dimension with Person 1 (AI track) before
    # Phase 1's migration is finalized — this WILL require a migration change
    # if wrong, since existing data can't easily be resized.
    embedding = Column(Vector(384), nullable=True)
    amenities = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "property_type IN ('flat', 'house_land')",
            name="ck_listing_property_type",
        ),
    )

    # Relationships
    broker = relationship("Broker", back_populates="listings")
    leads = relationship("Lead", back_populates="listing")

    def __repr__(self) -> str:
        return f"<Listing id={self.id} title={self.title!r} type={self.property_type}>"
