from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class Activity(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activities"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    session_worker_id: Mapped[str] = mapped_column(
        ForeignKey("session_workers.id"), nullable=False, index=True
    )
    ergonomic_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("ergonomic_events.id"), index=True
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    load_category: Mapped[str | None] = mapped_column(String(100))
    load_score: Mapped[int | None] = mapped_column(Integer)
    coupling_score: Mapped[int | None] = mapped_column(Integer)
    activity_score: Mapped[int | None] = mapped_column(Integer)
    wrist_twist_score: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[str | None] = mapped_column(String(255))
