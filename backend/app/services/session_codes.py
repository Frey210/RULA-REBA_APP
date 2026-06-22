from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.models.session import Session


def create_session_code(db: DbSession) -> str:
    today = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"SESSION_{today}_"
    count = db.scalar(
        select(func.count()).select_from(Session).where(Session.session_code.like(f"{prefix}%"))
    )
    return f"{prefix}{count + 1:03d}"
