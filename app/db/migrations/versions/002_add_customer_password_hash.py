"""Add password_hash column to customer table.

Revision ID: 002_add_customer_password_hash
Revises: 001_gist_index_listing_location
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002_add_customer_password_hash"
down_revision = "001_gist_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the column as nullable first so existing rows don't block ALTER
    op.add_column("customer", sa.Column("password_hash", sa.String(), nullable=True))
    # If there are existing customers without a password, set a placeholder
    # (they will need to reset their password)
    op.execute("UPDATE customer SET password_hash = 'NEEDS_RESET' WHERE password_hash IS NULL")
    # Now enforce NOT NULL
    op.alter_column("customer", "password_hash", nullable=False)


def downgrade() -> None:
    op.drop_column("customer", "password_hash")
