"""event review workflow

Revision ID: 20260627_0005
Revises: 20260627_0004
Create Date: 2026-06-27 03:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260627_0005"
down_revision: str | None = "20260627_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.add_column(sa.Column("ergonomic_event_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_activities_ergonomic_event_id", "ergonomic_events", ["ergonomic_event_id"], ["id"]
        )
        batch_op.create_index("ix_activities_ergonomic_event_id", ["ergonomic_event_id"])

    with op.batch_alter_table("assessments") as batch_op:
        batch_op.add_column(sa.Column("ergonomic_event_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("provisional_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("provisional_risk_level", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("review_notes", sa.String(length=2000), nullable=True))
        batch_op.create_foreign_key(
            "fk_assessments_ergonomic_event_id",
            "ergonomic_events",
            ["ergonomic_event_id"],
            ["id"],
        )
        batch_op.create_index("ix_assessments_ergonomic_event_id", ["ergonomic_event_id"])
        batch_op.create_unique_constraint(
            "uq_assessments_event_type", ["ergonomic_event_id", "assessment_type"]
        )

    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.add_column(sa.Column("ergonomic_event_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_snapshots_ergonomic_event_id", "ergonomic_events", ["ergonomic_event_id"], ["id"]
        )
        batch_op.create_index("ix_snapshots_ergonomic_event_id", ["ergonomic_event_id"])


def downgrade() -> None:
    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.drop_index("ix_snapshots_ergonomic_event_id")
        batch_op.drop_constraint("fk_snapshots_ergonomic_event_id", type_="foreignkey")
        batch_op.drop_column("ergonomic_event_id")

    with op.batch_alter_table("assessments") as batch_op:
        batch_op.drop_constraint("uq_assessments_event_type", type_="unique")
        batch_op.drop_index("ix_assessments_ergonomic_event_id")
        batch_op.drop_constraint("fk_assessments_ergonomic_event_id", type_="foreignkey")
        batch_op.drop_column("review_notes")
        batch_op.drop_column("provisional_risk_level")
        batch_op.drop_column("provisional_score")
        batch_op.drop_column("ergonomic_event_id")

    with op.batch_alter_table("activities") as batch_op:
        batch_op.drop_index("ix_activities_ergonomic_event_id")
        batch_op.drop_constraint("fk_activities_ergonomic_event_id", type_="foreignkey")
        batch_op.drop_column("ergonomic_event_id")
