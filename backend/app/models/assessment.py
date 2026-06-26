from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import UuidPrimaryKeyMixin, utcnow


class Assessment(UuidPrimaryKeyMixin, Base):
    __tablename__ = "assessments"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    session_worker_id: Mapped[str] = mapped_column(
        ForeignKey("session_workers.id"), nullable=False, index=True
    )
    ergonomic_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("ergonomic_events.id"), index=True
    )
    activity_id: Mapped[str | None] = mapped_column(ForeignKey("activities.id"))
    assessment_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    assessment_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(100), nullable=False)
    provisional_score: Mapped[int | None] = mapped_column(Integer)
    provisional_risk_level: Mapped[str | None] = mapped_column(String(100))
    review_notes: Mapped[str | None] = mapped_column(String(2000))
    score_a: Mapped[int | None] = mapped_column(Integer)
    score_b: Mapped[int | None] = mapped_column(Integer)
    breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_detection_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
