from datetime import UTC, datetime
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated

import httpx
import threading
import uuid
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
from app.models.edge_event import EdgeEvent
from app.models.user import User
from app.models.worker import Worker
from app.schemas.ergonomic_event import ErgonomicEventRead
from app.schemas.session import SessionCreate, SessionRead, SessionWorkerAssign, SessionWorkerRead
from app.schemas.session_summary import ScoreAggregate, SessionExposureSummary, WorkerExposureSummary
from app.services.event_engine import backfill_session_events, resolve_active_events_for_session
from app.services.session_codes import create_session_code
from app.services.exposure_intervals import merged_duration_ms
from app.services.edge_devices import device_state_lock

router = APIRouter()
session_control_lock = threading.RLock()


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
    if session.status in {"running", "preparing", "stopping"}:
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
            *((report.metadata_json or {}).get("archive_path") for report in reports),
            *((report.metadata_json or {}).get("excel_path") for report in reports),
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
    db.execute(sql_delete(EdgeEvent).where(EdgeEvent.payload["session_id"].as_string().in_([session.id, session.session_code])))
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
    with session_control_lock, device_state_lock:
        return _start_session(session_id, current_user, db)


def _start_session(session_id: str, current_user: User, db: DbSession) -> Session:
    session = _get_owned_session(session_id, current_user, db)
    if session.status not in {"created", "review_pending", "failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session cannot be started")
    cameras = _session_cameras(session, current_user, db)
    if not cameras:
        raise HTTPException(409, "Select and pair at least one camera before starting")
    for other in db.scalars(select(Session).where(Session.status.in_(["preparing", "running", "stopping"]), Session.id != session.id)):
        if set((other.metadata_json or {}).get("camera_node_ids", [])) & {c.cam_id for c in cameras}:
            raise HTTPException(409, "A selected camera is already in another session")
    session.status = "preparing"
    session.metadata_json = {**(session.metadata_json or {}),
                             "preparing_at": datetime.now(UTC).isoformat(),
                             "edge_runs": {c.cam_id: str(uuid.uuid4()) for c in cameras}}
    db.commit()
    edge_results = _start_edges_for_session(session, current_user, db)
    success = all(result["status"] == "started" for result in edge_results)
    if not success:
        _stop_edges_for_session(session, current_user, db)
    session.status = "running" if success else "failed"
    session.started_at = session.started_at or datetime.now(UTC)
    session.stopped_at = None
    session.metadata_json = {
        **(session.metadata_json or {}),
        "edge_start_results": edge_results,
        "edge_stop_results": [],
        "lease_confirmed_at": datetime.now(UTC).isoformat(),
        "operator_last_seen": datetime.now(UTC).isoformat(),
    }
    db.commit()
    db.refresh(session)
    if not success:
        details = "; ".join(f"{r['cam_id']}: {r['detail']}" for r in edge_results if r["status"] != "started")
        raise HTTPException(503, f"Session did not start. {details}")
    return session


@router.post("/{session_id}/operator-heartbeat", status_code=204)
def operator_heartbeat(session_id: str, current_user: Annotated[User, Depends(get_current_user)],
                       db: Annotated[DbSession, Depends(get_db)]) -> Response:
    with session_control_lock:
        session = _get_owned_session(session_id, current_user, db)
        db.refresh(session)
        if session.status in {"preparing", "running"}:
            session.metadata_json = {**(session.metadata_json or {}), "operator_last_seen": datetime.now(UTC).isoformat()}
            db.commit()
    return Response(status_code=204)


@router.post("/{session_id}/stop", response_model=SessionRead)
def stop_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Session:
    with session_control_lock, device_state_lock:
        return _stop_session(session_id, current_user, db)


def _stop_session(session_id: str, current_user: User, db: DbSession) -> Session:
    session = _get_owned_session(session_id, current_user, db)
    if session.status not in {"running", "stopping", "preparing"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is not running")
    session.status = "stopping"
    db.commit()
    edge_results = _stop_edges_for_session(session, current_user, db)
    success = all(result["status"] == "stopped" for result in edge_results)
    stopped_at = datetime.now(UTC)
    resolve_active_events_for_session(db, session, stopped_at)
    session.status = "review_pending" if success else "stopping"
    session.stopped_at = stopped_at
    session.metadata_json = {
        **(session.metadata_json or {}),
        "edge_stop_results": edge_results,
        "stop_requested_at": stopped_at.isoformat(),
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
            .where(ErgonomicEvent.session_id == session.id, ErgonomicEvent.event_type.notin_(["worker_entered", "worker_left"]))
        .order_by(ErgonomicEvent.started_at.desc(), ErgonomicEvent.created_at.desc())
    ).all()
    reviewed_types: dict[str, list[str]] = {}
    for event_id, assessment_type in db.execute(
        select(Assessment.ergonomic_event_id, Assessment.assessment_type).where(
            Assessment.session_id == session.id,
            Assessment.ergonomic_event_id.is_not(None),
            Assessment.assessment_status == "reviewed",
        )
    ):
        reviewed_types.setdefault(event_id, []).append(assessment_type)
    return [
        _event_read(event, session_worker, worker, reviewed_types.get(event.id, []))
        for event, session_worker, worker in rows
    ]


@router.get("/{session_id}/summary", response_model=SessionExposureSummary)
def get_session_summary(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> SessionExposureSummary:
    session = _get_owned_session(session_id, current_user, db)
    backfill_session_events(db, session)
    worker_rows = db.execute(
        select(SessionWorker, Worker)
        .outerjoin(Worker, SessionWorker.worker_id == Worker.id)
        .where(SessionWorker.session_id == session.id)
        .order_by(SessionWorker.created_at)
    ).all()
    events = list(
        db.scalars(select(ErgonomicEvent).where(ErgonomicEvent.session_id == session.id))
    )
    reviewed_event_ids = set(
        db.scalars(
            select(Assessment.ergonomic_event_id).where(
                Assessment.session_id == session.id,
                Assessment.ergonomic_event_id.is_not(None),
                Assessment.assessment_status == "reviewed",
            )
        )
    )
    now = session.stopped_at or datetime.now(UTC)
    summaries = [
        _worker_summary(session_worker, worker, events, reviewed_event_ids, now)
        for session_worker, worker in worker_rows
    ]
    worker_keys = {row.id: row.worker_id or row.id for row, _ in worker_rows}
    grouped_risk = {}
    for event in events:
        if event.event_type == "high_risk_posture":
            grouped_risk.setdefault(worker_keys.get(event.session_worker_id, event.session_worker_id), []).append(event)
    return SessionExposureSummary(
        session_id=session.id,
        worker_count=len(set(worker_keys.values())),
        event_count=len(events),
        high_risk_event_count=sum(row.high_risk_event_count for row in summaries),
        sustained_event_count=sum(row.sustained_event_count for row in summaries),
        high_risk_duration_ms=sum(merged_duration_ms(group) for group in grouped_risk.values()),
        reviewed_event_count=len(reviewed_event_ids),
        workers=summaries,
    )


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
        camera_node_id=session_worker.camera_node_id,
        run_id=session_worker.run_id,
        tracking_id=session_worker.tracking_id,
        identity_status=session_worker.identity_status,
        reid_confidence=session_worker.reid_confidence,
        confirmed_at=session_worker.confirmed_at,
    )


def _event_read(
    event: ErgonomicEvent,
    session_worker: SessionWorker,
    worker: Worker | None,
    reviewed_assessment_types: list[str],
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
        reviewed_assessment_types=sorted(reviewed_assessment_types),
    )


def _worker_summary(
    session_worker: SessionWorker,
    worker: Worker | None,
    events: list[ErgonomicEvent],
    reviewed_event_ids: set[str | None],
    now: datetime,
) -> WorkerExposureSummary:
    worker_events = [event for event in events if event.session_worker_id == session_worker.id]
    observed = next(
        (event for event in worker_events if event.event_type == "worker_observed"),
        None,
    )
    metadata = observed.metadata_json if observed else {}
    score_stats = metadata.get("score_stats") if isinstance(metadata, dict) else {}
    high_risk_events = [
        event for event in worker_events if event.event_type == "high_risk_posture"
    ]
    sustained_events = [
        event for event in worker_events if event.event_type == "sustained_high_risk"
    ]
    return WorkerExposureSummary(
        session_worker_id=session_worker.id,
        worker_id=session_worker.worker_id,
        worker_name=worker.name if worker else None,
        employee_number=worker.employee_number if worker else None,
        edge_worker_id=session_worker.edge_worker_id,
        first_seen_at=_metadata_datetime(metadata.get("first_seen_at")),
        last_seen_at=_metadata_datetime(metadata.get("last_seen_at")),
        detection_count=int(metadata.get("detection_count") or 0),
        high_risk_event_count=len(high_risk_events),
        sustained_event_count=len(sustained_events),
        high_risk_duration_ms=sum(_event_duration(event, now) for event in high_risk_events),
        reviewed_event_count=sum(event.id in reviewed_event_ids for event in worker_events),
        rula=_score_aggregate(score_stats, "rula"),
        reba=_score_aggregate(score_stats, "reba"),
    )


def _score_aggregate(score_stats: object, score_type: str) -> ScoreAggregate:
    values = score_stats.get(score_type, {}) if isinstance(score_stats, dict) else {}
    count = int(values.get("count") or 0) if isinstance(values, dict) else 0
    total = int(values.get("sum") or 0) if isinstance(values, dict) else 0
    peak = int(values.get("peak") or 0) if isinstance(values, dict) else 0
    return ScoreAggregate(
        average=round(total / count, 2) if count else None,
        peak=peak or None,
        samples=count,
    )


def _event_duration(event: ErgonomicEvent, now: datetime) -> int:
    if event.duration_ms is not None:
        return event.duration_ms
    started_at = event.started_at if event.started_at.tzinfo else event.started_at.replace(tzinfo=UTC)
    ended_at = now if now.tzinfo else now.replace(tzinfo=UTC)
    return max(0, int((ended_at - started_at).total_seconds() * 1000))


def _metadata_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _start_edges_for_session(session: Session, current_user: User, db: DbSession) -> list[dict]:
    from app.services.edge_devices import edge_request, refresh_camera
    cameras = _session_cameras(session, current_user, db)
    session_code = session.session_code
    run_ids = session.metadata_json["edge_runs"]
    results = {}
    targets = {}
    for camera in cameras:
        refresh_camera(camera)
        results[camera.cam_id] = {"cam_id": camera.cam_id, "status": "error",
            "detail": "Camera did not become ready. Check its connection, pairing, and USB camera."}
        if camera.status == "online" and (camera.metadata_json or {}).get("health", {}).get("camera_available"):
            # HTTP workers receive plain connection data, never the shared SQLAlchemy session/models.
            targets[camera.cam_id] = SimpleNamespace(id=camera.id, cam_id=camera.cam_id, owner_user_id=camera.owner_user_id,
                node_credential_hash=camera.node_credential_hash, metadata_json=dict(camera.metadata_json))
    if len(targets) != len(cameras):
        return list(results.values())

    def start(cam_id):
        run_id = run_ids[cam_id]
        try:
            camera = targets[cam_id]
            response = edge_request(camera, "POST", "/detection/start",
                json={"session_id": session_code, "run_id": run_id,
                      "backend_timestamp_ms": int(datetime.now(UTC).timestamp() * 1000)}, timeout=16)
            state = response.json()
            if not state.get("ready") or not state.get("running") or state.get("run_id") != run_id or state.get("session_id") != session_code:
                raise ValueError("Pipeline did not confirm this session")
            return {"cam_id": cam_id, "status": "started", "detail": "Camera ready"}
        except (httpx.HTTPError, ValueError):
            return results[cam_id]

    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="camera-start") as pool:
        pending = {pool.submit(start, cam_id) for cam_id in targets}
        while pending:
            completed, pending = wait(pending, timeout=3, return_when=FIRST_COMPLETED)
            for future in completed:
                result = future.result()
                results[result["cam_id"]] = result
            for cam_id, result in results.items():
                if result["status"] != "started":
                    continue
                try:
                    edge_request(targets[cam_id], "POST", "/detection/lease", timeout=1.2,
                                 json={"session_id": session_code, "run_id": run_ids[cam_id]})
                except (httpx.HTTPError, ValueError):
                    results[cam_id] = {"cam_id": cam_id, "status": "error", "detail": "Camera lost readiness during startup. Check its connection and retry."}
    return list(results.values())


def _stop_edges_for_session(session: Session, current_user: User, db: DbSession) -> list[dict]:
    from app.services.edge_devices import edge_request
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
            state = edge_request(camera, "GET", "/detection/status").json()
            expected_run = (session.metadata_json or {}).get("edge_runs", {}).get(camera.cam_id)
            if state.get("running") and state.get("run_id") != expected_run:
                raise ValueError("Camera is running a different session")
            response = edge_request(camera, "POST", "/detection/stop", timeout=9)
            if response.json().get("running"):
                raise ValueError("Pipeline has not stopped")
            results.append(
                {
                    "cam_id": camera.cam_id,
                    "status": "stopped" if response.is_success else "error",
                    "detail": "Camera stopped",
                }
            )
        except (httpx.HTTPError, ValueError):
            results.append({"cam_id": camera.cam_id, "status": "error", "detail": "Waiting for camera stop or lease expiry"})
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
    from app.core.config import settings
    path = Path(file_path).resolve()
    if not path.is_relative_to(settings.media_root.resolve()):
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
    try:
        path.parent.rmdir()
    except OSError:
        pass
