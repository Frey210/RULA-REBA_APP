from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class DevicePairing(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_pairings"

    camera_node_id: Mapped[str | None] = mapped_column(ForeignKey("camera_nodes.id"), index=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    pairing_code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

