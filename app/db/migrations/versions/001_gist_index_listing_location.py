"""Add GiST index on listing.location for geospatial query performance.

Revision ID: 001_gist_index
Revises:
Create Date: 2026-08-31

Note: A GiST index is required for PostGIS geometry columns.  Without it,
ST_DWithin and ST_Contains both fall back to a sequential scan — order-of-
magnitude slower for even moderate datasets.  Applied here rather than in
the initial schema migration so it can be independently reviewed and rolled
back if needed.
"""

from alembic import op


# revision identifiers, used by Alembic
revision = "001_gist_index"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create a GiST spatial index on listing.location.

    ``postgresql_using='gist'`` is required — BTree (the default) cannot
    index geometry columns.
    """
    op.create_index(
        "ix_listing_location",
        "listing",
        ["location"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    """Drop the GiST spatial index."""
    op.drop_index("ix_listing_location", table_name="listing")
