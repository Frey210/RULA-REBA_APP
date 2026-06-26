from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.activity import Activity
from app.models.assessment import Assessment
from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.ergonomic_event import ErgonomicEvent
from app.models.session import Session
from app.models.snapshot import Snapshot
from app.models.user import User
from app.schemas.event_review import (
    EventDetailRead,
    EventReviewRead,
    EventReviewUpsert,
    EventSnapshotRead,
)
from app.services.scoring import calculate_score
from app.services.snapshot_capture import capture_event_snapshot

router = APIRouter()


@router.get("/{session_id}/events/{event_id}", response_model=EventDetailRead)
def get_event_detail(
    session_id: str,
    event_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> EventDetailRead:
    session, event = _owned_event(session_id, event_id, current_user, db)
    detection = db.get(Detection, event.source_detection_id) if event.source_detection_id else None
    metadata = _detection_metadata(detection)
    reviews = db.scalars(
        select(Assessment)
        .where(Assessment.ergonomic_event_id == event.id)
        .order_by(Assessment.assessment_type)
    )
    snapshots = db.scalars(
        select(Snapshot)
        .where(Snapshot.ergonomic_event_id == event.id)
        .order_by(Snapshot.captured_at.desc())
    )
    return EventDetailRead(
        id=event.id,
        angles=metadata.get("angles") if isinstance(metadata.get("angles"), dict) else {},
        assessment_quality=(
            metadata.get("assessment_quality")
            if isinstance(metadata.get("assessment_quality"), dict)
            else {}
        ),
        provisional_scores={
            score_type: metadata[score_type]
            for score_type in ("rula", "reba")
            if isinstance(metadata.get(score_type), dict)
        },
        reviews=[_review_read(review, db) for review in reviews],
        snapshots=[_snapshot_read(session, snapshot) for snapshot in snapshots],
    )


@router.put(
    "/{session_id}/events/{event_id}/reviews/{assessment_type}",
    response_model=EventReviewRead,
)
def save_event_review(
    session_id: str,
    event_id: str,
    assessment_type: Literal["rula", "reba"],
    payload: EventReviewUpsert,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> EventReviewRead:
    session, event = _owned_event(session_id, event_id, current_user, db)
    detection = db.get(Detection, event.source_detection_id) if event.source_detection_id else None
    if detection is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This event has no source detection to review",
        )

    metadata = _detection_metadata(detection)
    angles = {
        key: value
        for key, value in (metadata.get("angles") or {}).items()
        if isinstance(value, int | float)
    }
    manual = _manual_inputs(assessment_type, payload)
    final_result = calculate_score(assessment_type, angles, manual)
    provisional = metadata.get(assessment_type)
    if not isinstance(provisional, dict) or not isinstance(provisional.get("score"), int | float):
        provisional = calculate_score(assessment_type, angles, {})

    review = db.scalar(
        select(Assessment).where(
            Assessment.ergonomic_event_id == event.id,
            Assessment.assessment_type == assessment_type,
        )
    )
    activity = db.get(Activity, review.activity_id) if review and review.activity_id else None
    if activity is None:
        activity = Activity(
            session_id=session.id,
            session_worker_id=event.session_worker_id,
            ergonomic_event_id=event.id,
            activity_type=f"{assessment_type}_manual_review",
        )
        db.add(activity)
        db.flush()

    activity.load_score = manual.get("load_score")
    activity.coupling_score = manual.get("coupling_score")
    activity.activity_score = manual.get("activity_score")
    activity.wrist_twist_score = manual.get("wrist_twist_score")
    activity.confirmed_by = current_user.email

    now = datetime.now(UTC)
    breakdown = {
        **final_result["breakdown"],
        "manual_inputs": manual,
        "assessment_quality": metadata.get("assessment_quality") or {},
    }
    if review is None:
        review = Assessment(
            session_id=session.id,
            session_worker_id=event.session_worker_id,
            ergonomic_event_id=event.id,
            activity_id=activity.id,
            assessment_type=assessment_type,
            assessment_status="reviewed",
            score=final_result["score"],
            risk_level=final_result["risk_level"],
            breakdown=breakdown,
            source_detection_ids=[detection.id],
            calculated_at=now,
        )
        db.add(review)
    review.activity_id = activity.id
    review.assessment_status = "reviewed"
    review.score = final_result["score"]
    review.risk_level = final_result["risk_level"]
    review.score_a = final_result["breakdown"].get("score_a")
    review.score_b = final_result["breakdown"].get("score_b")
    review.provisional_score = int(provisional["score"])
    review.provisional_risk_level = str(
        provisional.get("risk_level") or provisional.get("risk") or "Unknown"
    )
    review.review_notes = payload.notes.strip() if payload.notes else None
    review.breakdown = breakdown
    review.source_detection_ids = [detection.id]
    review.calculated_at = now
    db.commit()
    db.refresh(review)
    return _review_read(review, db)


@router.post(
    "/{session_id}/events/{event_id}/snapshots",
    response_model=EventSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def capture_snapshot(
    session_id: str,
    event_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> EventSnapshotRead:
    session, event = _owned_event(session_id, event_id, current_user, db)
    camera = db.get(CameraNode, event.camera_node_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event camera not found")
    snapshot = capture_event_snapshot(
        db, session, camera, event, capture_reason="manual_review_capture"
    )
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The edge camera did not provide a snapshot",
        )
    db.commit()
    db.refresh(snapshot)
    return _snapshot_read(session, snapshot)


@router.get("/{session_id}/events/{event_id}/snapshots/{snapshot_id}/content")
def get_snapshot_content(
    session_id: str,
    event_id: str,
    snapshot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> FileResponse:
    _owned_event(session_id, event_id, current_user, db)
    snapshot = db.get(Snapshot, snapshot_id)
    if snapshot is None or snapshot.ergonomic_event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    path = Path(snapshot.file_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot file not found")
    return FileResponse(
        path,
        media_type=str(snapshot.metadata_json.get("content_type") or "image/jpeg"),
        headers={"Cache-Control": "private, max-age=60"},
    )


def _owned_event(
    session_id: str,
    event_id: str,
    current_user: User,
    db: DbSession,
) -> tuple[Session, ErgonomicEvent]:
    session = db.get(Session, session_id)
    if session is None or session.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    event = db.get(ErgonomicEvent, event_id)
    if event is None or event.session_id != session.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return session, event


def _detection_metadata(detection: Detection | None) -> dict:
    if detection is None or not isinstance(detection.raw_payload, dict):
        return {}
    raw_detection = detection.raw_payload.get("detection")
    if not isinstance(raw_detection, dict):
        return {}
    metadata = raw_detection.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _manual_inputs(
    assessment_type: Literal["rula", "reba"], payload: EventReviewUpsert
) -> dict[str, int]:
    if assessment_type == "reba":
        return {
            "load_score": payload.load_score,
            "coupling_score": payload.coupling_score or 0,
            "activity_score": payload.activity_score,
        }
    if payload.activity_score > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="RULA muscle use score must be 0 or 1",
        )
    return {
        "load_score": payload.load_score,
        "activity_score": payload.activity_score,
        "wrist_twist_score": payload.wrist_twist_score or 1,
    }


def _review_read(review: Assessment, db: DbSession) -> EventReviewRead:
    activity = db.get(Activity, review.activity_id) if review.activity_id else None
    manual_inputs = review.breakdown.get("manual_inputs", {})
    return EventReviewRead(
        id=review.id,
        assessment_type=review.assessment_type,
        assessment_status=review.assessment_status,
        provisional_score=review.provisional_score,
        provisional_risk_level=review.provisional_risk_level,
        score=review.score,
        risk_level=review.risk_level,
        manual_inputs=manual_inputs if isinstance(manual_inputs, dict) else {},
        breakdown=review.breakdown,
        notes=review.review_notes,
        reviewed_by=activity.confirmed_by if activity else None,
        calculated_at=review.calculated_at,
    )


def _snapshot_read(session: Session, snapshot: Snapshot) -> EventSnapshotRead:
    return EventSnapshotRead(
        id=snapshot.id,
        snapshot_type=snapshot.snapshot_type,
        captured_at=snapshot.captured_at,
        content_url=(
            f"/api/v1/sessions/{session.id}/events/{snapshot.ergonomic_event_id}"
            f"/snapshots/{snapshot.id}/content"
        ),
        metadata=snapshot.metadata_json,
    )
