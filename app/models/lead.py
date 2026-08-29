"""Lead ORM model — cross-team contract defined in AGENTS.md §4."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Lead(Base):
    """Tracks a customer inquiry on a specific listing for broker analytics."""

    __tablename__ = "lead"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(
        Integer, ForeignKey("listing.id"), nullable=False, index=True
    )
    customer_id = Column(
        Integer, ForeignKey("customer.id"), nullable=False, index=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    listing = relationship("Listing", back_populates="leads")
    customer = relationship("Customer", back_populates="leads")

    def __repr__(self) -> str:
        return f"<Lead id={self.id} listing={self.listing_id} customer={self.customer_id}>"
