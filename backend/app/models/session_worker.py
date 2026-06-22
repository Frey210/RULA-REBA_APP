from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class SessionWorker(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "session_workers"
    __table_args__ = (UniqueConstraint("session_id", "edge_worker_id"),)

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    worker_id: Mapped[str | None] = mapped_column(ForeignKey("workers.id"), index=True)
    edge_worker_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tracking_id: Mapped[int | None] = mapped_column(Integer)
    identity_status: Mapped[str] = mapped_column(String(50), default="unconfirmed", nullable=False)
    reid_confidence: Mapped[float | None] = mapped_column(Float)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

