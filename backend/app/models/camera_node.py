from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class CameraNode(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "camera_nodes"

    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    cam_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(255))
    device_type: Mapped[str | None] = mapped_column(String(100))
    stream_uri: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="offline", index=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    node_credential_hash: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

    owner = relationship("User", back_populates="camera_nodes")

