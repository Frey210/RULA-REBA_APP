from datetime import UTC, datetime
import threading

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.session import Session
from app.models.session_worker import SessionWorker
from app.models.edge_event import EdgeEvent
from app.models.snapshot import Snapshot
from app.schemas.edge import EdgeDetectionEvent
from app.services.event_engine import process_detection_for_events, process_presence_timeouts
from app.services.pose_quality import normalize_measurements

# shortcut: one writer per desktop backend; use database row locks for multi-server deployments.
recording_write_lock = threading.RLock()


def persist_detection_event(db: DbSession, event: EdgeDetectionEvent) -> int:
    session = db.scalar(
        select(Session).where(or_(Session.id == event.session_id, Session.session_code == event.session_id))
    )
    camera = db.scalar(select(CameraNode).where(CameraNode.cam_id == event.cam_id))
    if session is None or camera is None:
        raise ValueError("Unknown session or camera")
    if (session.status not in {"preparing", "running"} or session.owner_user_id != camera.owner_user_id
            or camera.cam_id not in (session.metadata_json or {}).get("camera_node_ids", [])
            or (session.metadata_json or {}).get("edge_runs", {}).get(camera.cam_id) != event.run_id):
        raise ValueError("Camera/run does not belong to this active session")
    key = f"{camera.id}:{event.run_id}:{event.frame_id}"
    if db.scalar(select(EdgeEvent.id).where(EdgeEvent.event_key == key)):
        return -1
    previous = db.scalar(select(EdgeEvent).where(EdgeEvent.camera_node_id == camera.id,
        EdgeEvent.payload["run_id"].as_string() == event.run_id).order_by(EdgeEvent.received_at.desc()).limit(1))
    if previous and (event.frame_id <= previous.payload["frame_id"] or event.timestamp < previous.payload["timestamp"]):
        return -1
    if abs(datetime.now(UTC).timestamp() * 1000 - event.timestamp) > 30_000:
        raise ValueError("Stale frame or device clock is incorrect")
    header = event.model_dump(exclude={"detections"})
    db.add(EdgeEvent(camera_node_id=camera.id, event_type="detection", event_key=key, payload=header,
                     received_at=datetime.now(UTC)))

    observed_at = datetime.fromtimestamp(event.timestamp / 1000, tz=UTC)
    inserted = 0
    for detection in event.detections:
        normalize_measurements(detection)
        session_worker = db.scalar(
            select(SessionWorker).where(
                SessionWorker.session_id == session.id,
                SessionWorker.edge_worker_id == detection.worker_id,
                SessionWorker.camera_node_id == camera.id,
                SessionWorker.run_id == event.run_id,
            )
        )
        identity_status = str(detection.metadata.get("identity_status") or "unconfirmed")
        if session_worker is None:
            session_worker = SessionWorker(
                session_id=session.id,
                camera_node_id=camera.id,
                run_id=event.run_id,
                edge_worker_id=detection.worker_id,
                tracking_id=detection.tracking_id,
                identity_status=identity_status,
                reid_confidence=detection.reid_confidence,
            )
            db.add(session_worker)
            db.flush()
        else:
            session_worker.tracking_id = detection.tracking_id
            if session_worker.worker_id is None:
                session_worker.identity_status = identity_status
            session_worker.reid_confidence = detection.reid_confidence

        detection_row = Detection(
            session_id=session.id,
            camera_node_id=camera.id,
            session_worker_id=session_worker.id,
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
            angles=detection.metadata.get("angles"),
            raw_payload={
                "event": header,
                "detection": detection.model_dump(),
            },
        )
        db.add(detection_row)
        db.flush()
        created_events = process_detection_for_events(
            db, session, camera, session_worker, detection_row, detection
        )
        db.flush()
        for created_event in created_events:
            source = db.get(Detection, created_event.source_detection_id)
            if source and not db.scalar(select(Snapshot.id).where(Snapshot.ergonomic_event_id == created_event.id,
                                                                 Snapshot.detection_id == source.id)):
                db.add(Snapshot(session_id=session.id, camera_node_id=camera.id,
                                session_worker_id=session_worker.id, ergonomic_event_id=created_event.id,
                                detection_id=source.id, snapshot_type="event_evidence", file_path="",
                                captured_at=source.observed_at, metadata_json={"status": "pending"}))
        inserted += 1

    process_presence_timeouts(db, session, observed_at)
    db.commit()
    return inserted
