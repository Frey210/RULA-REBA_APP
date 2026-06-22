"""initial schema

Revision ID: 20260623_0001
Revises:
Create Date: 2026-06-23 01:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260623_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "camera_nodes",
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("cam_id", sa.String(length=100), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("device_type", sa.String(length=100), nullable=True),
        sa.Column("stream_uri", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("node_credential_hash", sa.String(length=255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_camera_nodes_cam_id"), "camera_nodes", ["cam_id"], unique=True)
    op.create_index(op.f("ix_camera_nodes_last_seen_at"), "camera_nodes", ["last_seen_at"])
    op.create_index(op.f("ix_camera_nodes_owner_user_id"), "camera_nodes", ["owner_user_id"])
    op.create_index(op.f("ix_camera_nodes_status"), "camera_nodes", ["status"])

    op.create_table(
        "workers",
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("employee_number", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("position", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workers_department"), "workers", ["department"])
    op.create_index(op.f("ix_workers_employee_number"), "workers", ["employee_number"], unique=True)
    op.create_index(op.f("ix_workers_owner_user_id"), "workers", ["owner_user_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"])

    op.create_table(
        "device_pairings",
        sa.Column("camera_node_id", sa.String(length=36), nullable=True),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("pairing_code_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_node_id"], ["camera_nodes.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_device_pairings_camera_node_id"), "device_pairings", ["camera_node_id"])
    op.create_index(op.f("ix_device_pairings_owner_user_id"), "device_pairings", ["owner_user_id"])
    op.create_index(op.f("ix_device_pairings_status"), "device_pairings", ["status"])

    op.create_table(
        "sessions",
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("session_code", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_owner_user_id"), "sessions", ["owner_user_id"])
    op.create_index(op.f("ix_sessions_session_code"), "sessions", ["session_code"], unique=True)
    op.create_index(op.f("ix_sessions_started_at"), "sessions", ["started_at"])
    op.create_index(op.f("ix_sessions_status"), "sessions", ["status"])

    op.create_table(
        "session_workers",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("worker_id", sa.String(length=36), nullable=True),
        sa.Column("edge_worker_id", sa.String(length=100), nullable=False),
        sa.Column("tracking_id", sa.Integer(), nullable=True),
        sa.Column("identity_status", sa.String(length=50), nullable=False),
        sa.Column("reid_confidence", sa.Float(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "edge_worker_id"),
    )
    op.create_index(op.f("ix_session_workers_edge_worker_id"), "session_workers", ["edge_worker_id"])
    op.create_index(op.f("ix_session_workers_session_id"), "session_workers", ["session_id"])
    op.create_index(op.f("ix_session_workers_worker_id"), "session_workers", ["worker_id"])

    op.create_table(
        "detections",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("camera_node_id", sa.String(length=36), nullable=False),
        sa.Column("session_worker_id", sa.String(length=36), nullable=True),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("frame_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp_ms", sa.BigInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edge_worker_id", sa.String(length=100), nullable=False),
        sa.Column("tracking_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reid_confidence", sa.Float(), nullable=True),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("keypoints", sa.JSON(), nullable=False),
        sa.Column("angles", sa.JSON(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["camera_node_id"], ["camera_nodes.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["session_worker_id"], ["session_workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_detections_camera_node_id"), "detections", ["camera_node_id"])
    op.create_index(op.f("ix_detections_edge_worker_id"), "detections", ["edge_worker_id"])
    op.create_index(op.f("ix_detections_observed_at"), "detections", ["observed_at"])
    op.create_index(op.f("ix_detections_session_id"), "detections", ["session_id"])
    op.create_index(op.f("ix_detections_session_worker_id"), "detections", ["session_worker_id"])
    op.create_index(op.f("ix_detections_timestamp_ms"), "detections", ["timestamp_ms"])

    op.create_table(
        "activities",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("session_worker_id", sa.String(length=36), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("load_category", sa.String(length=100), nullable=True),
        sa.Column("load_score", sa.Integer(), nullable=True),
        sa.Column("coupling_score", sa.Integer(), nullable=True),
        sa.Column("activity_score", sa.Integer(), nullable=True),
        sa.Column("wrist_twist_score", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["session_worker_id"], ["session_workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activities_activity_type"), "activities", ["activity_type"])
    op.create_index(op.f("ix_activities_session_id"), "activities", ["session_id"])
    op.create_index(op.f("ix_activities_session_worker_id"), "activities", ["session_worker_id"])

    op.create_table(
        "assessments",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("session_worker_id", sa.String(length=36), nullable=False),
        sa.Column("activity_id", sa.String(length=36), nullable=True),
        sa.Column("assessment_type", sa.String(length=20), nullable=False),
        sa.Column("assessment_status", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=100), nullable=False),
        sa.Column("score_a", sa.Integer(), nullable=True),
        sa.Column("score_b", sa.Integer(), nullable=True),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("source_detection_ids", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["session_worker_id"], ["session_workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessments_assessment_status"), "assessments", ["assessment_status"])
    op.create_index(op.f("ix_assessments_assessment_type"), "assessments", ["assessment_type"])
    op.create_index(op.f("ix_assessments_score"), "assessments", ["score"])
    op.create_index(op.f("ix_assessments_session_id"), "assessments", ["session_id"])
    op.create_index(op.f("ix_assessments_session_worker_id"), "assessments", ["session_worker_id"])

    op.create_table(
        "snapshots",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("detection_id", sa.String(length=36), nullable=True),
        sa.Column("camera_node_id", sa.String(length=36), nullable=False),
        sa.Column("session_worker_id", sa.String(length=36), nullable=True),
        sa.Column("snapshot_type", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("thumbnail_path", sa.String(length=1000), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["camera_node_id"], ["camera_nodes.id"]),
        sa.ForeignKeyConstraint(["detection_id"], ["detections.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["session_worker_id"], ["session_workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_snapshots_camera_node_id"), "snapshots", ["camera_node_id"])
    op.create_index(op.f("ix_snapshots_captured_at"), "snapshots", ["captured_at"])
    op.create_index(op.f("ix_snapshots_session_id"), "snapshots", ["session_id"])
    op.create_index(op.f("ix_snapshots_session_worker_id"), "snapshots", ["session_worker_id"])

    op.create_table(
        "review_items",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("session_worker_id", sa.String(length=36), nullable=True),
        sa.Column("review_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("resolved_payload", sa.JSON(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["session_worker_id"], ["session_workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_items_review_type"), "review_items", ["review_type"])
    op.create_index(op.f("ix_review_items_session_id"), "review_items", ["session_id"])
    op.create_index(op.f("ix_review_items_session_worker_id"), "review_items", ["session_worker_id"])
    op.create_index(op.f("ix_review_items_status"), "review_items", ["status"])

    op.create_table(
        "reports",
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("generated_by", sa.String(length=255), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_owner_user_id"), "reports", ["owner_user_id"])
    op.create_index(op.f("ix_reports_report_type"), "reports", ["report_type"])
    op.create_index(op.f("ix_reports_session_id"), "reports", ["session_id"])
    op.create_index(op.f("ix_reports_status"), "reports", ["status"])

    op.create_table(
        "edge_events",
        sa.Column("camera_node_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["camera_node_id"], ["camera_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_edge_events_camera_node_id"), "edge_events", ["camera_node_id"])
    op.create_index(op.f("ix_edge_events_event_type"), "edge_events", ["event_type"])
    op.create_index(op.f("ix_edge_events_received_at"), "edge_events", ["received_at"])


def downgrade() -> None:
    for table in [
        "edge_events",
        "reports",
        "review_items",
        "snapshots",
        "assessments",
        "activities",
        "detections",
        "session_workers",
        "sessions",
        "device_pairings",
        "refresh_tokens",
        "workers",
        "camera_nodes",
        "users",
    ]:
        op.drop_table(table)

