from io import BytesIO

import httpx
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.models.camera_node import CameraNode
from app.models.ergonomic_event import ErgonomicEvent
from app.models.session import Session
from app.models.snapshot import Snapshot

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


def capture_event_snapshot(
    db: DbSession,
    session: Session,
    camera: CameraNode,
    event: ErgonomicEvent,
    *,
    capture_reason: str = "event_created",
) -> Snapshot | None:
    edge_base_url = str((camera.metadata_json or {}).get("edge_base_url") or "").rstrip("/")
    if not edge_base_url:
        return None

    try:
        response = httpx.get(
            f"{edge_base_url}/snapshot/latest",
            params={"overlay": "true", "quality": 76},
            timeout=2.5,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    content = response.content
    if not content or len(content) > MAX_SNAPSHOT_BYTES:
        return None
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format
    except (UnidentifiedImageError, OSError):
        return None
    if image_format != "JPEG":
        return None

    directory = settings.media_root / "session-snapshots" / session.owner_user_id / session.id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{event.id}.jpg"
    temporary = path.with_suffix(".upload")
    temporary.write_bytes(content)
    temporary.replace(path)

    snapshot = db.scalar(
        select(Snapshot).where(Snapshot.ergonomic_event_id == event.id).limit(1)
    )
    if snapshot is None:
        snapshot = Snapshot(
            session_id=session.id,
            detection_id=event.source_detection_id,
            ergonomic_event_id=event.id,
            camera_node_id=camera.id,
            session_worker_id=event.session_worker_id,
            snapshot_type="event_evidence",
            file_path=str(path),
            captured_at=event.started_at,
            metadata_json={},
        )
        db.add(snapshot)
    snapshot.file_path = str(path)
    snapshot.metadata_json = {
        "content_type": "image/jpeg",
        "width": width,
        "height": height,
        "file_size": len(content),
        "capture_reason": capture_reason,
        "source": "edge_latest_annotated_frame",
    }
    return snapshot
