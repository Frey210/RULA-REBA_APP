"""worker enrollment images

Revision ID: 20260626_0002
Revises: 20260623_0001
Create Date: 2026-06-26 06:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260626_0002"
down_revision: str | None = "20260623_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "worker_enrollment_images",
        sa.Column("worker_id", sa.String(length=36), nullable=False),
        sa.Column("view", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_id", "view"),
    )
    op.create_index(op.f("ix_worker_enrollment_images_worker_id"), "worker_enrollment_images", ["worker_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_worker_enrollment_images_worker_id"), table_name="worker_enrollment_images")
    op.drop_table("worker_enrollment_images")
