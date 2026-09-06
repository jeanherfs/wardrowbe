"""add item-rating learning metrics

Revision ID: b7c8d9e0f1a2
Revises: f8a9b0c1d2e3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_learning_profiles",
        sa.Column("learned_type_scores", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "user_learning_profiles",
        sa.Column("learned_brand_scores", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "user_learning_profiles",
        sa.Column("average_item_fit", sa.Numeric(3, 2), nullable=True),
    )
    op.add_column(
        "user_learning_profiles",
        sa.Column("average_item_style", sa.Numeric(3, 2), nullable=True),
    )
    op.add_column(
        "user_learning_profiles",
        sa.Column("items_rated", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("user_learning_profiles", "items_rated")
    op.drop_column("user_learning_profiles", "average_item_style")
    op.drop_column("user_learning_profiles", "average_item_fit")
    op.drop_column("user_learning_profiles", "learned_brand_scores")
    op.drop_column("user_learning_profiles", "learned_type_scores")
