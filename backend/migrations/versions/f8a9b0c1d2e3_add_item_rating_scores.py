"""add item fit and style rating scores

Revision ID: f8a9b0c1d2e3
Revises: f7a8b9c0d1e2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clothing_items", sa.Column("fit_score", sa.Numeric(2, 1), nullable=True))
    op.add_column("clothing_items", sa.Column("style_score", sa.Numeric(2, 1), nullable=True))


def downgrade() -> None:
    op.drop_column("clothing_items", "style_score")
    op.drop_column("clothing_items", "fit_score")
