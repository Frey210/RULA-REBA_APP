from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class ErgonomicEvent(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ergonomic_events"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    camera_node_id: Mapped[str] = mapped_column(ForeignKey("camera_nodes.id"), nullable=False, index=True)
    session_worker_id: Mapped[str] = mapped_column(ForeignKey("session_workers.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), default="info", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    score_type: Mapped[str | None] = mapped_column(String(20))
    score: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str | None] = mapped_column(String(100))
    source_detection_id: Mapped[str | None] = mapped_column(ForeignKey("detections.id"), index=True)
    last_detection_id: Mapped[str | None] = mapped_column(ForeignKey("detections.id"), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

