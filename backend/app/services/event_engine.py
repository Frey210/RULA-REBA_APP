from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.ergonomic_event import ErgonomicEvent
from app.models.session import Session
from app.models.session_worker import SessionWorker
from app.schemas.edge import EdgeDetection
from app.services.scoring import calculate_score

HIGH_RISK_EVENT = "high_risk_posture"
WORKER_OBSERVED_EVENT = "worker_observed"


def process_detection_for_events(
    db: DbSession,
    session: Session,
    camera: CameraNode,
    session_worker: SessionWorker,
    detection_row: Detection,
    edge_detection: EdgeDetection,
) -> None:
    _ensure_worker_observed_event(db, session, camera, session_worker, detection_row, edge_detection)

    assessment = _assessment_from_detection(edge_detection)
    active_high_risk = _active_event(db, session_worker.id, HIGH_RISK_EVENT)
    if assessment is None or not assessment["is_high_risk"]:
        if active_high_risk:
            _resolve_event(active_high_risk, detection_row.observed_at, detection_row.id)
        return

    if active_high_risk is None:
        db.add(
            ErgonomicEvent(
                session_id=session.id,
                camera_node_id=camera.id,
                session_worker_id=session_worker.id,
                event_type=HIGH_RISK_EVENT,
                status="active",
                severity=assessment["severity"],
                started_at=detection_row.observed_at,
                score_type=assessment["score_type"],
                score=assessment["score"],
                risk_level=assessment["risk_level"],
                source_detection_id=detection_row.id,
                last_detection_id=detection_row.id,
                confidence=edge_detection.confidence,
                metadata_json={"assessment": assessment["raw"]},
            )
        )
        return

    active_high_risk.last_detection_id = detection_row.id
    active_high_risk.score_type = assessment["score_type"]
    active_high_risk.score = assessment["score"]
    active_high_risk.risk_level = assessment["risk_level"]
    active_high_risk.severity = assessment["severity"]
    active_high_risk.confidence = edge_detection.confidence
    active_high_risk.metadata_json = {"assessment": assessment["raw"]}


def resolve_active_events_for_session(db: DbSession, session: Session, ended_at: datetime) -> None:
    active_events = db.scalars(
        select(ErgonomicEvent).where(
            ErgonomicEvent.session_id == session.id,
            ErgonomicEvent.status == "active",
            ErgonomicEvent.event_type == HIGH_RISK_EVENT,
        )
    )
    for event in active_events:
        _resolve_event(event, ended_at, event.last_detection_id)


def backfill_session_events(db: DbSession, session: Session) -> int:
    """Materialize events for detections recorded before the event engine existed."""
    if db.scalar(
        select(ErgonomicEvent.id).where(ErgonomicEvent.session_id == session.id).limit(1)
    ) is not None:
        return 0

    cameras = {
        camera.id: camera
        for camera in db.scalars(
            select(CameraNode).where(
                CameraNode.id.in_(
                    select(Detection.camera_node_id).where(Detection.session_id == session.id)
                )
            )
        )
    }
    workers = {
        worker.id: worker
        for worker in db.scalars(
            select(SessionWorker).where(SessionWorker.session_id == session.id)
        )
    }
    rows = db.scalars(
        select(Detection)
        .where(Detection.session_id == session.id, Detection.session_worker_id.is_not(None))
        .order_by(Detection.observed_at, Detection.frame_id)
    )

    processed = 0
    for detection_row in rows:
        camera = cameras.get(detection_row.camera_node_id)
        session_worker = workers.get(detection_row.session_worker_id)
        raw_detection = detection_row.raw_payload.get("detection", {})
        if camera is None or session_worker is None or not isinstance(raw_detection, dict):
            continue
        try:
            edge_detection = EdgeDetection.model_validate(raw_detection)
        except ValueError:
            continue
        process_detection_for_events(
            db,
            session,
            camera,
            session_worker,
            detection_row,
            edge_detection,
        )
        db.flush()
        processed += 1

    if session.stopped_at:
        resolve_active_events_for_session(db, session, session.stopped_at)
    if processed:
        db.commit()
    return processed


def _ensure_worker_observed_event(
    db: DbSession,
    session: Session,
    camera: CameraNode,
    session_worker: SessionWorker,
    detection_row: Detection,
    edge_detection: EdgeDetection,
) -> None:
    existing = db.scalar(
        select(ErgonomicEvent.id)
        .where(
            ErgonomicEvent.session_id == session.id,
            ErgonomicEvent.session_worker_id == session_worker.id,
            ErgonomicEvent.event_type == WORKER_OBSERVED_EVENT,
        )
        .limit(1)
    )
    if existing is not None:
        return

    db.add(
        ErgonomicEvent(
            session_id=session.id,
            camera_node_id=camera.id,
            session_worker_id=session_worker.id,
            event_type=WORKER_OBSERVED_EVENT,
            status="resolved",
            severity="info",
            started_at=detection_row.observed_at,
            ended_at=detection_row.observed_at,
            duration_ms=0,
            source_detection_id=detection_row.id,
            last_detection_id=detection_row.id,
            confidence=edge_detection.confidence,
            metadata_json={"edge_worker_id": edge_detection.worker_id},
        )
    )


def _active_event(db: DbSession, session_worker_id: str, event_type: str) -> ErgonomicEvent | None:
    return db.scalar(
        select(ErgonomicEvent).where(
            ErgonomicEvent.session_worker_id == session_worker_id,
            ErgonomicEvent.event_type == event_type,
            ErgonomicEvent.status == "active",
        )
    )


def _resolve_event(event: ErgonomicEvent, ended_at: datetime, last_detection_id: str | None) -> None:
    event.status = "resolved"
    event.ended_at = ended_at
    event.last_detection_id = last_detection_id
    started_at = event.started_at if event.started_at.tzinfo else event.started_at.replace(tzinfo=UTC)
    resolved_at = ended_at if ended_at.tzinfo else ended_at.replace(tzinfo=UTC)
    event.duration_ms = max(0, int((resolved_at - started_at).total_seconds() * 1000))


def _assessment_from_detection(detection: EdgeDetection) -> dict[str, Any] | None:
    assessments = [
        assessment
        for score_type in ("reba", "rula")
        if (assessment := _normalize_assessment(score_type, detection.metadata.get(score_type)))
    ]
    if assessments:
        return max(assessments, key=lambda item: item["severity_rank"])

    angles = detection.metadata.get("angles")
    if isinstance(angles, dict):
        try:
            reba = calculate_score("reba", angles, {})
            rula = calculate_score("rula", angles, {})
        except (TypeError, ValueError):
            return None
        return max(
            (_normalize_assessment("reba", reba), _normalize_assessment("rula", rula)),
            key=lambda item: item["severity_rank"] if item else -1,
        )
    return None


def _normalize_assessment(score_type: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    raw_score = value.get("score")
    if not isinstance(raw_score, int | float):
        return None
    score = int(raw_score)
    risk_level = str(value.get("risk_level") or value.get("risk") or "")

    if score_type == "reba":
        severity_rank = 4 if score >= 11 else 3 if score >= 8 else 2 if score >= 4 else 1
        is_high_risk = score >= 8
    else:
        severity_rank = 4 if score >= 7 else 3 if score >= 5 else 2 if score >= 3 else 1
        is_high_risk = score >= 5

    severity = "critical" if severity_rank >= 4 else "high" if severity_rank == 3 else "medium" if severity_rank == 2 else "low"
    return {
        "score_type": score_type,
        "score": score,
        "risk_level": risk_level,
        "severity": severity,
        "severity_rank": severity_rank,
        "is_high_risk": is_high_risk,
        "raw": value,
    }
