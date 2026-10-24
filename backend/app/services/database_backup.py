import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import settings


def backup_database() -> None:
    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return
    source = Path(url.database).resolve()
    if not source.is_file():
        return
    with sqlite3.connect(source) as connection:
        exists = connection.execute("SELECT name FROM sqlite_master WHERE name='alembic_version'").fetchone()
        current = connection.execute("SELECT version_num FROM alembic_version").fetchone() if exists else None
        if current and current[0] == "20261024_0007":
            return
        destination = source.with_name(f"{source.stem}.pre-integrity-{datetime.now(UTC):%Y%m%d-%H%M%S}.sqlite3")
        with sqlite3.connect(destination) as target:
            connection.backup(target)
