from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class Report(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_path: Mapped[str | None] = mapped_column(String(1000))
    generated_by: Mapped[str | None] = mapped_column(String(255))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

