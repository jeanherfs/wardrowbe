"""add structured item measurements

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clothing_items", sa.Column("measurements", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("clothing_items", "measurements")
