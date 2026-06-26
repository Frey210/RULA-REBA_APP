"""ergonomic events

Revision ID: 20260627_0004
Revises: 20260627_0003
Create Date: 2026-06-27 01:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260627_0004"
down_revision: str | None = "20260627_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ergonomic_events",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("camera_node_id", sa.String(length=36), nullable=False),
        sa.Column("session_worker_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("score_type", sa.String(length=20), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(length=100), nullable=True),
        sa.Column("source_detection_id", sa.String(length=36), nullable=True),
        sa.Column("last_detection_id", sa.String(length=36), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_node_id"], ["camera_nodes.id"]),
        sa.ForeignKeyConstraint(["last_detection_id"], ["detections.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["session_worker_id"], ["session_workers.id"]),
        sa.ForeignKeyConstraint(["source_detection_id"], ["detections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ergonomic_events_camera_node_id"), "ergonomic_events", ["camera_node_id"])
    op.create_index(op.f("ix_ergonomic_events_ended_at"), "ergonomic_events", ["ended_at"])
    op.create_index(op.f("ix_ergonomic_events_event_type"), "ergonomic_events", ["event_type"])
    op.create_index(op.f("ix_ergonomic_events_last_detection_id"), "ergonomic_events", ["last_detection_id"])
    op.create_index(op.f("ix_ergonomic_events_session_id"), "ergonomic_events", ["session_id"])
    op.create_index(op.f("ix_ergonomic_events_session_worker_id"), "ergonomic_events", ["session_worker_id"])
    op.create_index(op.f("ix_ergonomic_events_severity"), "ergonomic_events", ["severity"])
    op.create_index(op.f("ix_ergonomic_events_source_detection_id"), "ergonomic_events", ["source_detection_id"])
    op.create_index(op.f("ix_ergonomic_events_started_at"), "ergonomic_events", ["started_at"])
    op.create_index(op.f("ix_ergonomic_events_status"), "ergonomic_events", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ergonomic_events_status"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_started_at"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_source_detection_id"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_severity"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_session_worker_id"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_session_id"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_last_detection_id"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_event_type"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_ended_at"), table_name="ergonomic_events")
    op.drop_index(op.f("ix_ergonomic_events_camera_node_id"), table_name="ergonomic_events")
    op.drop_table("ergonomic_events")

