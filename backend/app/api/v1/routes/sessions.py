from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.activity import Activity
from app.models.assessment import Assessment
from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.ergonomic_event import ErgonomicEvent
from app.models.report import Report
from app.models.review_item import ReviewItem
from app.models.session import Session
from app.models.session_worker import SessionWorker
from app.models.snapshot import Snapshot
from app.models.user import User
from app.models.worker import Worker
from app.schemas.ergonomic_event import ErgonomicEventRead
from app.schemas.session import SessionCreate, SessionRead, SessionWorkerAssign, SessionWorkerRead
from app.services.event_engine import backfill_session_events, resolve_active_events_for_session
from app.services.session_codes import create_session_code

router = APIRouter()


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Session:
    if payload.camera_node_ids:
        known_count = db.scalar(
            select(func.count())
            .select_from(CameraNode)
            .where(
                CameraNode.owner_user_id == current_user.id,
                CameraNode.cam_id.in_(payload.camera_node_ids),
            )
        )
        if known_count != len(payload.camera_node_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more camera nodes are not paired to this user",
            )

    session = Session(
        owner_user_id=current_user.id,
        session_code=create_session_code(db),
        notes=payload.notes,
        metadata_json={"camera_node_ids": payload.camera_node_ids},
        created_by=current_user.email,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[SessionRead])
def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[Session]:
    return list(
        db.scalars(
            select(Session)
            .where(Session.owner_user_id == current_user.id)
            .order_by(Session.created_at.desc())
        )
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Response:
    session = _get_owned_session(session_id, current_user, db)
    if session.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop the running session before deleting it",
        )

    snapshots = list(db.scalars(select(Snapshot).where(Snapshot.session_id == session.id)))
    reports = list(db.scalars(select(Report).where(Report.session_id == session.id)))
    media_paths = [
        path
        for path in (
            *(snapshot.file_path for snapshot in snapshots),
            *(snapshot.thumbnail_path for snapshot in snapshots),
            *(report.file_path for report in reports),
        )
        if path
    ]

    db.execute(sql_delete(Assessment).where(Assessment.session_id == session.id))
    db.execute(sql_delete(Snapshot).where(Snapshot.session_id == session.id))
    db.execute(sql_delete(Activity).where(Activity.session_id == session.id))
    db.execute(sql_delete(ReviewItem).where(ReviewItem.session_id == session.id))
    db.execute(sql_delete(ErgonomicEvent).where(ErgonomicEvent.session_id == session.id))
    db.execute(sql_delete(Detection).where(Detection.session_id == session.id))
    db.execute(sql_delete(Report).where(Report.session_id == session.id))
    db.execute(sql_delete(SessionWorker).where(SessionWorker.session_id == session.id))
    db.delete(session)
    db.commit()

    for media_path in media_paths:
        _remove_media_file(media_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{session_id}/start", response_model=SessionRead)
def start_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Session:
    session = _get_owned_session(session_id, current_user, db)
    if session.status not in {"created", "review_pending"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session cannot be started")
    edge_results = _start_edges_for_session(session, current_user, db)
    session.status = "running"
    session.started_at = datetime.now(UTC)
    session.stopped_at = None
    session.metadata_json = {
        **(session.metadata_json or {}),
        "edge_start_results": edge_results,
        "edge_stop_results": [],
    }
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=SessionRead)
def stop_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Session:
    session = _get_owned_session(session_id, current_user, db)
    if session.status != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is not running")
    edge_results = _stop_edges_for_session(session, current_user, db)
    stopped_at = datetime.now(UTC)
    resolve_active_events_for_session(db, session, stopped_at)
    session.status = "review_pending"
    session.stopped_at = stopped_at
    session.metadata_json = {
        **(session.metadata_json or {}),
        "edge_stop_results": edge_results,
    }
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/complete", response_model=SessionRead)
def complete_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Session:
    session = _get_owned_session(session_id, current_user, db)
    if session.status != "review_pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a session pending review can be completed",
        )
    session.status = "completed"
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}/events", response_model=list[ErgonomicEventRead])
def list_session_events(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[ErgonomicEventRead]:
    session = _get_owned_session(session_id, current_user, db)
    backfill_session_events(db, session)
    rows = db.execute(
        select(ErgonomicEvent, SessionWorker, Worker)
        .join(SessionWorker, ErgonomicEvent.session_worker_id == SessionWorker.id)
        .outerjoin(Worker, SessionWorker.worker_id == Worker.id)
        .where(ErgonomicEvent.session_id == session.id)
        .order_by(ErgonomicEvent.started_at.desc(), ErgonomicEvent.created_at.desc())
    ).all()
    return [_event_read(event, session_worker, worker) for event, session_worker, worker in rows]


@router.get("/{session_id}/workers", response_model=list[SessionWorkerRead])
def list_session_workers(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[SessionWorkerRead]:
    session = _get_owned_session(session_id, current_user, db)
    rows = db.execute(
        select(SessionWorker, Worker)
        .outerjoin(Worker, SessionWorker.worker_id == Worker.id)
        .where(SessionWorker.session_id == session.id)
        .order_by(SessionWorker.created_at)
    ).all()
    return [_session_worker_read(session_worker, worker) for session_worker, worker in rows]


@router.patch("/{session_id}/workers/{session_worker_id}", response_model=SessionWorkerRead)
def assign_session_worker(
    session_id: str,
    session_worker_id: str,
    payload: SessionWorkerAssign,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> SessionWorkerRead:
    session = _get_owned_session(session_id, current_user, db)
    session_worker = db.get(SessionWorker, session_worker_id)
    if session_worker is None or session_worker.session_id != session.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session worker not found")

    worker = None
    if payload.worker_id:
        worker = db.get(Worker, payload.worker_id)
        if worker is None or worker.owner_user_id != current_user.id or not worker.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    session_worker.worker_id = worker.id if worker else None
    session_worker.identity_status = "confirmed" if worker else "unconfirmed"
    session_worker.confirmed_at = datetime.now(UTC) if worker else None
    db.commit()
    db.refresh(session_worker)
    return _session_worker_read(session_worker, worker)


def _get_owned_session(session_id: str, current_user: User, db: DbSession) -> Session:
    session = db.get(Session, session_id)
    if session is None or session.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def _session_worker_read(session_worker: SessionWorker, worker: Worker | None) -> SessionWorkerRead:
    return SessionWorkerRead(
        id=session_worker.id,
        session_id=session_worker.session_id,
        worker_id=session_worker.worker_id,
        worker_name=worker.name if worker else None,
        employee_number=worker.employee_number if worker else None,
        edge_worker_id=session_worker.edge_worker_id,
        tracking_id=session_worker.tracking_id,
        identity_status=session_worker.identity_status,
        reid_confidence=session_worker.reid_confidence,
        confirmed_at=session_worker.confirmed_at,
    )


def _event_read(
    event: ErgonomicEvent,
    session_worker: SessionWorker,
    worker: Worker | None,
) -> ErgonomicEventRead:
    return ErgonomicEventRead(
        id=event.id,
        session_id=event.session_id,
        camera_node_id=event.camera_node_id,
        session_worker_id=event.session_worker_id,
        worker_id=session_worker.worker_id,
        worker_name=worker.name if worker else None,
        employee_number=worker.employee_number if worker else None,
        edge_worker_id=session_worker.edge_worker_id,
        event_type=event.event_type,
        status=event.status,
        severity=event.severity,
        started_at=event.started_at,
        ended_at=event.ended_at,
        duration_ms=event.duration_ms,
        score_type=event.score_type,
        score=event.score,
        risk_level=event.risk_level,
        confidence=event.confidence,
        metadata_json=event.metadata_json,
    )


def _start_edges_for_session(session: Session, current_user: User, db: DbSession) -> list[dict]:
    cameras = _session_cameras(session, current_user, db)
    results = []
    for camera in cameras:
        edge_base_url = (camera.metadata_json or {}).get("edge_base_url")
        if not edge_base_url:
            results.append(
                {
                    "cam_id": camera.cam_id,
                    "status": "skipped",
                    "detail": "Camera node does not have edge_base_url metadata",
                }
            )
            continue

        try:
            response = httpx.post(
                f"{edge_base_url}/detection/start",
                json={"session_id": session.session_code},
                timeout=5,
            )
            results.append(
                {
                    "cam_id": camera.cam_id,
                    "status": "started" if response.is_success else "error",
                    "detail": response.text,
                }
            )
        except httpx.HTTPError as exc:
            results.append({"cam_id": camera.cam_id, "status": "error", "detail": str(exc)})
    return results


def _stop_edges_for_session(session: Session, current_user: User, db: DbSession) -> list[dict]:
    cameras = _session_cameras(session, current_user, db)
    results = []
    for camera in cameras:
        edge_base_url = (camera.metadata_json or {}).get("edge_base_url")
        if not edge_base_url:
            results.append(
                {
                    "cam_id": camera.cam_id,
                    "status": "skipped",
                    "detail": "Camera node does not have edge_base_url metadata",
                }
            )
            continue

        try:
            response = httpx.post(f"{edge_base_url}/detection/stop", timeout=5)
            results.append(
                {
                    "cam_id": camera.cam_id,
                    "status": "stopped" if response.is_success else "error",
                    "detail": response.text,
                }
            )
        except httpx.HTTPError as exc:
            results.append({"cam_id": camera.cam_id, "status": "error", "detail": str(exc)})
    return results


def _session_cameras(session: Session, current_user: User, db: DbSession) -> list[CameraNode]:
    cam_ids = (session.metadata_json or {}).get("camera_node_ids") or []
    if not cam_ids:
        return []
    return list(
        db.scalars(
            select(CameraNode).where(
                CameraNode.owner_user_id == current_user.id,
                CameraNode.cam_id.in_(cam_ids),
            )
        )
    )


def _remove_media_file(file_path: str) -> None:
    path = Path(file_path)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
    try:
        path.parent.rmdir()
    except OSError:
        pass
