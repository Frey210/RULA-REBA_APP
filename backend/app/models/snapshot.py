from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import UuidPrimaryKeyMixin, utcnow


class Snapshot(UuidPrimaryKeyMixin, Base):
    __tablename__ = "snapshots"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    detection_id: Mapped[str | None] = mapped_column(ForeignKey("detections.id"))
    ergonomic_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("ergonomic_events.id"), index=True
    )
    camera_node_id: Mapped[str] = mapped_column(ForeignKey("camera_nodes.id"), nullable=False, index=True)
    session_worker_id: Mapped[str | None] = mapped_column(ForeignKey("session_workers.id"), index=True)
    snapshot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1000))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
