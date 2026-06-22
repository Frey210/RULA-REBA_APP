from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import UuidPrimaryKeyMixin, utcnow


class Detection(UuidPrimaryKeyMixin, Base):
    __tablename__ = "detections"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    camera_node_id: Mapped[str] = mapped_column(ForeignKey("camera_nodes.id"), nullable=False, index=True)
    session_worker_id: Mapped[str | None] = mapped_column(ForeignKey("session_workers.id"), index=True)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    frame_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    edge_worker_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tracking_id: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    reid_confidence: Mapped[float | None] = mapped_column(Float)
    bbox: Mapped[list] = mapped_column(JSON, nullable=False)
    keypoints: Mapped[dict] = mapped_column(JSON, nullable=False)
    angles: Mapped[dict | None] = mapped_column(JSON)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

