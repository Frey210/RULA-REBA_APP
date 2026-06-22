from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.session import Session
from app.schemas.edge import EdgeDetectionEvent


def persist_detection_event(db: DbSession, event: EdgeDetectionEvent) -> int:
    session = db.scalar(
        select(Session).where(or_(Session.id == event.session_id, Session.session_code == event.session_id))
    )
    camera = db.scalar(select(CameraNode).where(CameraNode.cam_id == event.cam_id))
    if session is None or camera is None:
        return 0

    observed_at = datetime.fromtimestamp(event.timestamp / 1000, tz=UTC)
    inserted = 0
    for detection in event.detections:
        db.add(
            Detection(
                session_id=session.id,
                camera_node_id=camera.id,
                schema_version=event.schema_version,
                frame_id=event.frame_id,
                timestamp_ms=event.timestamp,
                observed_at=observed_at,
                edge_worker_id=detection.worker_id,
                tracking_id=detection.tracking_id,
                confidence=detection.confidence,
                reid_confidence=detection.reid_confidence,
                bbox=detection.bbox,
                keypoints=detection.keypoints.model_dump(),
                raw_payload={
                    "event": event.model_dump(),
                    "detection": detection.model_dump(),
                },
            )
        )
        inserted += 1

    if inserted:
        db.commit()
    return inserted

