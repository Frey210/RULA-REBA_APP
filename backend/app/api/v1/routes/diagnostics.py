import json
import platform
import shutil
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.report import Report
from app.models.session import Session
from app.models.user import User
from app.services.edge_devices import camera_is_fresh

router = APIRouter()


@router.get("/diagnostics")
def download_diagnostics(current_user: Annotated[User, Depends(get_current_user)],
                         db: Annotated[DbSession, Depends(get_db)]) -> Response:
    sessions = list(db.scalars(select(Session).where(Session.owner_user_id == current_user.id)))
    cameras = list(db.scalars(select(CameraNode).where(CameraNode.owner_user_id == current_user.id)))
    url = make_url(settings.database_url)
    db_path = Path(url.database).resolve() if url.get_backend_name() == "sqlite" and url.database else None
    storage = settings.media_root.resolve()
    while not storage.exists():
        storage = storage.parent
    data = dict(format_version=1, app_version="0.2.2", generated_at=datetime.now(UTC).isoformat(),
        runtime=dict(os=platform.system(), release=platform.release(), python=platform.python_version()),
        storage=dict(database_bytes=db_path.stat().st_size if db_path and db_path.is_file() else None,
                     free_bytes=shutil.disk_usage(storage).free,
                     automatic_raw_deletion=False),
        recording=dict(session_count=len(sessions), active_count=sum(s.status in {"preparing", "running", "stopping"} for s in sessions),
            detection_count=db.scalar(select(func.count()).select_from(Detection).where(Detection.session_id.in_([s.id for s in sessions]))),
            report_count=db.scalar(select(func.count()).select_from(Report).where(Report.owner_user_id == current_user.id))),
        cameras=[dict(cam_id=c.cam_id, device_id=(c.metadata_json or {}).get("device_id"),
            online=camera_is_fresh(c), last_seen_at=c.last_seen_at.isoformat() if c.last_seen_at else None,
            health={key: (c.metadata_json or {}).get("health", {}).get(key) for key in
                    ("camera_available", "running", "ready", "frame_age_ms")}) for c in cameras])
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", json.dumps(data, indent=2))
        archive.writestr("README.txt", "ERGoSIGHT diagnostics. No credentials, account details, photos or raw logs included.\n"
            "Camera UUIDs and runtime/storage counters are included. Raw recordings are never automatically deleted.\n"
            "Use History to explicitly delete an unwanted stopped session, after downloading documentation if needed.\n")
    return Response(output.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": 'attachment; filename="ergosight-diagnostics.zip"', "Cache-Control": "private, no-store"})
