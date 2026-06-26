"""worker enrollment quality metadata

Revision ID: 20260627_0003
Revises: 20260626_0002
Create Date: 2026-06-27 00:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260627_0003"
down_revision: str | None = "20260626_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "worker_enrollment_images",
        sa.Column("quality_status", sa.String(length=30), nullable=False, server_default="review_needed"),
    )
    op.add_column(
        "worker_enrollment_images",
        sa.Column("quality_details_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("worker_enrollment_images", "quality_details_json")
    op.drop_column("worker_enrollment_images", "quality_status")
