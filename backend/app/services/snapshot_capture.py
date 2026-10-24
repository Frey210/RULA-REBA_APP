from io import BytesIO
import hashlib

import httpx
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.models.camera_node import CameraNode
from app.models.ergonomic_event import ErgonomicEvent
from app.models.session import Session
from app.models.snapshot import Snapshot
from app.models.detection import Detection
from app.models.assessment import Assessment
from app.services.edge_devices import edge_request
from uuid import uuid4

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

    detection = db.get(Detection, event.source_detection_id)
    if detection is None or db.scalar(select(Assessment.id).where(Assessment.ergonomic_event_id == event.id).limit(1)):
        return None
    previous = db.scalar(select(Snapshot).where(Snapshot.ergonomic_event_id == event.id, Snapshot.detection_id == detection.id))
    if previous and previous.file_path:
        return previous
    header = (detection.raw_payload or {}).get("event", {})
    run_id = header.get("run_id")
    if not run_id:
        return None
    try:
        response = edge_request(camera, "GET", f"/snapshot/frames/{detection.frame_id}",
                                params={"run_id": run_id, "overlay": "true"}, timeout=2)
        if response.headers.get("x-frame-id") != str(detection.frame_id) or response.headers.get("x-run-id") != run_id:
            return None
    except (httpx.HTTPError, ValueError):
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
    path = directory / f"{uuid4()}.jpg"
    temporary = path.with_suffix(".upload")
    temporary.write_bytes(content)
    temporary.replace(path)

    snapshot = previous
    if snapshot is None:
        snapshot = Snapshot(
            session_id=session.id,
            detection_id=event.source_detection_id,
            ergonomic_event_id=event.id,
            camera_node_id=camera.id,
            session_worker_id=event.session_worker_id,
            snapshot_type="event_evidence",
            file_path=str(path),
            captured_at=detection.observed_at,
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
        "source": "verified_source_frame",
        "status": "ready",
        "run_id": run_id,
        "frame_id": detection.frame_id,
        "checksum_sha256": hashlib.sha256(content).hexdigest(),
    }
    return snapshot


def capture_pending_evidence() -> None:
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        jobs = db.scalars(select(Snapshot).where(
            Snapshot.metadata_json["status"].as_string() == "pending"
        ).limit(4)).all()
        for job in jobs:
            event = db.get(ErgonomicEvent, job.ergonomic_event_id)
            if event is None or event.source_detection_id != job.detection_id:
                job.metadata_json = {"status": "superseded"}
                continue
            session = db.get(Session, event.session_id)
            camera = db.get(CameraNode, event.camera_node_id)
            snapshot = capture_event_snapshot(db, session, camera, event)
            if snapshot is None:
                job.metadata_json = {"status": "unavailable", "reason": "Source frame expired or device unavailable"}
        db.commit()
