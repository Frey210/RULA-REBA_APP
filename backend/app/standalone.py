import os
import sys
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

from app.main import app


def bundled_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / name


def run() -> None:
    from app.services.database_backup import backup_database
    backup_database()
    config = Config(str(bundled_path("alembic.ini")))
    config.set_main_option("script_location", str(bundled_path("alembic")))
    command.upgrade(config, "head")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="info")


if __name__ == "__main__":
    run()
