"""Scope observations to camera/run and deduplicate incoming frames."""
import sqlalchemy as sa
from alembic import op

revision = "20261024_0007"
down_revision = "20260628_0006"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    constraints = sa.inspect(connection).get_unique_constraints("session_workers")
    previous = next((c["name"] for c in constraints if c["column_names"] == ["session_id", "edge_worker_id"]), None)
    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s"}
    with op.batch_alter_table("session_workers", naming_convention=naming) as batch:
        batch.drop_constraint(previous or "uq_session_workers_session_id_edge_worker_id", type_="unique")
        batch.add_column(sa.Column("camera_node_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("run_id", sa.String(36), nullable=False, server_default="legacy"))
        batch.create_foreign_key("fk_session_workers_camera", "camera_nodes", ["camera_node_id"], ["id"])
        batch.create_unique_constraint("uq_session_worker_camera_run", ["session_id", "camera_node_id", "run_id", "edge_worker_id"])
    connection.execute(sa.text("UPDATE session_workers SET camera_node_id = (SELECT camera_node_id FROM detections WHERE session_worker_id = session_workers.id ORDER BY observed_at LIMIT 1)"))
    op.add_column("edge_events", sa.Column("event_key", sa.String(200), nullable=True))
    op.create_index("ix_edge_events_event_key", "edge_events", ["event_key"], unique=True)


def downgrade():
    # Splitting observations cannot be undone without merging people's histories.
    raise RuntimeError("Restore the pre-upgrade database backup to roll back this migration")
