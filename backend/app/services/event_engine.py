from datetime import UTC, datetime, timedelta
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
SUSTAINED_POSTURE_EVENT = "sustained_high_risk"
WORKER_OBSERVED_EVENT = "worker_observed"
WORKER_ENTERED_EVENT = "worker_entered"
WORKER_LEFT_EVENT = "worker_left"
PRESENCE_TIMEOUT = timedelta(seconds=3)
HIGH_RISK_RELEASE_GRACE = timedelta(seconds=1)
SUSTAINED_POSTURE_THRESHOLD = timedelta(seconds=10)


def process_detection_for_events(
    db: DbSession,
    session: Session,
    camera: CameraNode,
    session_worker: SessionWorker,
    detection_row: Detection,
    edge_detection: EdgeDetection,
) -> list[ErgonomicEvent]:
    created_events: list[ErgonomicEvent] = []
    observed_event = _update_worker_observation(
        db, session, camera, session_worker, detection_row, edge_detection
    )
    if observed_event:
        created_events.append(observed_event)

    assessments = _assessments_from_detection(edge_detection)
    primary = max(assessments, key=lambda item: item["severity_rank"], default=None)
    active_high_risk = _active_event(db, session_worker.id, HIGH_RISK_EVENT)
    if primary is None or not primary["is_high_risk"]:
        if active_high_risk and _release_grace_elapsed(active_high_risk, detection_row.observed_at):
            _resolve_event(active_high_risk, detection_row.observed_at, detection_row.id)
        return created_events

    if active_high_risk is None:
        event = ErgonomicEvent(
            session_id=session.id,
            camera_node_id=camera.id,
            session_worker_id=session_worker.id,
            event_type=HIGH_RISK_EVENT,
            status="active",
            severity=primary["severity"],
            started_at=detection_row.observed_at,
            score_type=primary["score_type"],
            score=primary["score"],
            risk_level=primary["risk_level"],
            source_detection_id=detection_row.id,
            last_detection_id=detection_row.id,
            confidence=edge_detection.confidence,
            metadata_json={
                "assessment": primary["raw"],
                "last_high_at": detection_row.observed_at.isoformat(),
                "score_stats": _score_stats({}, assessments),
                "sustained_emitted": False,
            },
        )
        db.add(event)
        created_events.append(event)
        return created_events

    metadata = dict(active_high_risk.metadata_json or {})
    metadata["last_high_at"] = detection_row.observed_at.isoformat()
    metadata["score_stats"] = _score_stats(metadata.get("score_stats"), assessments)
    if _is_more_severe(primary, active_high_risk):
        active_high_risk.score_type = primary["score_type"]
        active_high_risk.score = primary["score"]
        active_high_risk.risk_level = primary["risk_level"]
        active_high_risk.severity = primary["severity"]
        metadata["assessment"] = primary["raw"]
    active_high_risk.metadata_json = metadata
    active_high_risk.last_detection_id = detection_row.id
    active_high_risk.confidence = edge_detection.confidence

    if (
        not metadata.get("sustained_emitted")
        and _aware(detection_row.observed_at) - _aware(active_high_risk.started_at)
        >= SUSTAINED_POSTURE_THRESHOLD
    ):
        metadata["sustained_emitted"] = True
        active_high_risk.metadata_json = metadata
        sustained = ErgonomicEvent(
            session_id=session.id,
            camera_node_id=camera.id,
            session_worker_id=session_worker.id,
            event_type=SUSTAINED_POSTURE_EVENT,
            status="resolved",
            severity=active_high_risk.severity,
            started_at=active_high_risk.started_at,
            ended_at=detection_row.observed_at,
            duration_ms=_duration_ms(active_high_risk.started_at, detection_row.observed_at),
            score_type=active_high_risk.score_type,
            score=active_high_risk.score,
            risk_level=active_high_risk.risk_level,
            source_detection_id=active_high_risk.source_detection_id,
            last_detection_id=detection_row.id,
            confidence=edge_detection.confidence,
            metadata_json={"parent_event_id": active_high_risk.id},
        )
        db.add(sustained)
        created_events.append(sustained)
    return created_events


def process_presence_timeouts(db: DbSession, session: Session, observed_at: datetime) -> int:
    transitions = 0
    observed_events = db.scalars(
        select(ErgonomicEvent).where(
            ErgonomicEvent.session_id == session.id,
            ErgonomicEvent.event_type == WORKER_OBSERVED_EVENT,
        )
    )
    for observed_event in observed_events:
        metadata = dict(observed_event.metadata_json or {})
        if not metadata.get("presence_active"):
            continue
        last_seen = _parse_datetime(metadata.get("last_seen_at"))
        if last_seen is None or _aware(observed_at) - last_seen < PRESENCE_TIMEOUT:
            continue
        left_at = last_seen + PRESENCE_TIMEOUT
        db.add(
            _presence_transition(
                observed_event,
                WORKER_LEFT_EVENT,
                left_at,
                observed_event.last_detection_id,
            )
        )
        metadata["presence_active"] = False
        observed_event.metadata_json = metadata
        transitions += 1
    return transitions


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

    observed_events = db.scalars(
        select(ErgonomicEvent).where(
            ErgonomicEvent.session_id == session.id,
            ErgonomicEvent.event_type == WORKER_OBSERVED_EVENT,
        )
    )
    for observed_event in observed_events:
        metadata = dict(observed_event.metadata_json or {})
        if not metadata.get("presence_active"):
            continue
        db.add(
            _presence_transition(
                observed_event,
                WORKER_LEFT_EVENT,
                ended_at,
                observed_event.last_detection_id,
            )
        )
        metadata["presence_active"] = False
        observed_event.metadata_json = metadata


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


def _update_worker_observation(
    db: DbSession,
    session: Session,
    camera: CameraNode,
    session_worker: SessionWorker,
    detection_row: Detection,
    edge_detection: EdgeDetection,
) -> ErgonomicEvent | None:
    event = db.scalar(
        select(ErgonomicEvent)
        .where(
            ErgonomicEvent.session_id == session.id,
            ErgonomicEvent.session_worker_id == session_worker.id,
            ErgonomicEvent.event_type == WORKER_OBSERVED_EVENT,
        )
        .limit(1)
    )
    created = event is None
    if event is None:
        event = ErgonomicEvent(
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
            metadata_json={},
        )
        db.add(event)

    metadata = dict(event.metadata_json or {})
    was_present = bool(metadata.get("presence_active"))
    metadata.update(
        {
            "edge_worker_id": edge_detection.worker_id,
            "first_seen_at": metadata.get("first_seen_at") or detection_row.observed_at.isoformat(),
            "last_seen_at": detection_row.observed_at.isoformat(),
            "presence_active": True,
            "detection_count": int(metadata.get("detection_count") or 0) + 1,
            "score_stats": _score_stats(
                metadata.get("score_stats"), _assessments_from_detection(edge_detection)
            ),
        }
    )
    event.metadata_json = metadata
    event.ended_at = detection_row.observed_at
    event.duration_ms = _duration_ms(event.started_at, detection_row.observed_at)
    event.last_detection_id = detection_row.id
    event.confidence = edge_detection.confidence

    if not was_present:
        db.add(
            _presence_transition(
                event,
                WORKER_ENTERED_EVENT,
                detection_row.observed_at,
                detection_row.id,
            )
        )
    return event if created else None


def _presence_transition(
    observed_event: ErgonomicEvent,
    event_type: str,
    occurred_at: datetime,
    detection_id: str | None,
) -> ErgonomicEvent:
    return ErgonomicEvent(
        session_id=observed_event.session_id,
        camera_node_id=observed_event.camera_node_id,
        session_worker_id=observed_event.session_worker_id,
        event_type=event_type,
        status="resolved",
        severity="info",
        started_at=occurred_at,
        ended_at=occurred_at,
        duration_ms=0,
        source_detection_id=detection_id,
        last_detection_id=detection_id,
        confidence=observed_event.confidence,
        metadata_json={"edge_worker_id": (observed_event.metadata_json or {}).get("edge_worker_id")},
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
    event.duration_ms = _duration_ms(event.started_at, ended_at)


def _release_grace_elapsed(event: ErgonomicEvent, observed_at: datetime) -> bool:
    last_high = _parse_datetime((event.metadata_json or {}).get("last_high_at"))
    return last_high is None or _aware(observed_at) - last_high >= HIGH_RISK_RELEASE_GRACE


def _is_more_severe(assessment: dict[str, Any], event: ErgonomicEvent) -> bool:
    current = _normalize_assessment(event.score_type or "", {"score": event.score or 0})
    current_rank = current["severity_rank"] if current else 0
    return (assessment["severity_rank"], assessment["score"]) > (current_rank, event.score or 0)


def _score_stats(existing: Any, assessments: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    stats = {
        key: dict(value)
        for key, value in (existing.items() if isinstance(existing, dict) else [])
        if isinstance(value, dict)
    }
    for assessment in assessments:
        score_type = assessment["score_type"]
        score = int(assessment["score"])
        current = stats.get(score_type, {})
        stats[score_type] = {
            "sum": int(current.get("sum") or 0) + score,
            "count": int(current.get("count") or 0) + 1,
            "peak": max(int(current.get("peak") or 0), score),
            "last": score,
        }
    return stats


def _assessments_from_detection(detection: EdgeDetection) -> list[dict[str, Any]]:
    assessments = [
        assessment
        for score_type in ("reba", "rula")
        if (assessment := _normalize_assessment(score_type, detection.metadata.get(score_type)))
    ]
    if assessments:
        return assessments

    angles = detection.metadata.get("angles")
    if not isinstance(angles, dict):
        return []
    try:
        results = (calculate_score("reba", angles, {}), calculate_score("rula", angles, {}))
    except (TypeError, ValueError):
        return []
    return [
        assessment
        for score_type, result in zip(("reba", "rula"), results, strict=True)
        if (assessment := _normalize_assessment(score_type, result))
    ]


def _normalize_assessment(score_type: str, value: Any) -> dict[str, Any] | None:
    if score_type not in {"reba", "rula"} or not isinstance(value, dict):
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

    severity = (
        "critical"
        if severity_rank >= 4
        else "high"
        if severity_rank == 3
        else "medium"
        if severity_rank == 2
        else "low"
    )
    return {
        "score_type": score_type,
        "score": score,
        "risk_level": risk_level,
        "severity": severity,
        "severity_rank": severity_rank,
        "is_high_risk": is_high_risk,
        "raw": value,
    }


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return _aware(datetime.fromisoformat(value))
    except ValueError:
        return None


def _duration_ms(started_at: datetime, ended_at: datetime) -> int:
    return max(0, int((_aware(ended_at) - _aware(started_at)).total_seconds() * 1000))


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)
