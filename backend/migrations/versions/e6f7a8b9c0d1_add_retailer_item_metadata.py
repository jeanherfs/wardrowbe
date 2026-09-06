"""add retailer item metadata

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


retailer = sa.Enum("zalando", "mango", name="retailer")
return_status = sa.Enum("kept", "returned", name="return_status")
fit_rating = sa.Enum(
    "too_small",
    "slightly_small",
    "fits",
    "slightly_large",
    "too_large",
    name="fit_rating",
)


def upgrade() -> None:
    bind = op.get_bind()
    retailer.create(bind, checkfirst=True)
    return_status.create(bind, checkfirst=True)
    fit_rating.create(bind, checkfirst=True)
    op.add_column("clothing_items", sa.Column("retailer", retailer, nullable=True))
    op.add_column("clothing_items", sa.Column("retailer_product_id", sa.String(length=100), nullable=True))
    op.add_column("clothing_items", sa.Column("source_url", sa.String(length=2000), nullable=True))
    op.add_column("clothing_items", sa.Column("purchased_size", sa.String(length=50), nullable=True))
    op.add_column("clothing_items", sa.Column("purchased_color", sa.String(length=100), nullable=True))
    op.add_column("clothing_items", sa.Column("return_status", return_status, nullable=True))
    op.add_column("clothing_items", sa.Column("fit_rating", fit_rating, nullable=True))
    op.add_column("clothing_items", sa.Column("fit_notes", sa.Text(), nullable=True))
    op.add_column("clothing_items", sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "CREATE UNIQUE INDEX uq_clothing_items_retailer_identity "
        "ON clothing_items (user_id, retailer, retailer_product_id, purchased_size, purchased_color) "
        "NULLS NOT DISTINCT WHERE retailer IS NOT NULL AND retailer_product_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("uq_clothing_items_retailer_identity", table_name="clothing_items")
    op.drop_column("clothing_items", "imported_at")
    op.drop_column("clothing_items", "fit_notes")
    op.drop_column("clothing_items", "fit_rating")
    op.drop_column("clothing_items", "return_status")
    op.drop_column("clothing_items", "purchased_color")
    op.drop_column("clothing_items", "purchased_size")
    op.drop_column("clothing_items", "source_url")
    op.drop_column("clothing_items", "retailer_product_id")
    op.drop_column("clothing_items", "retailer")
    bind = op.get_bind()
    fit_rating.drop(bind, checkfirst=True)
    return_status.drop(bind, checkfirst=True)
    retailer.drop(bind, checkfirst=True)
