from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import UuidPrimaryKeyMixin, utcnow


class EdgeEvent(UuidPrimaryKeyMixin, Base):
    __tablename__ = "edge_events"

    camera_node_id: Mapped[str | None] = mapped_column(ForeignKey("camera_nodes.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

