import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.camera_node import CameraNode
from app.models.session import Session
from app.models.user import User
from app.services.edge_devices import edge_request, refresh_camera, device_state_lock
from app.services.event_engine import process_presence_timeouts
from app.services.detection_ingest import recording_write_lock

logger = logging.getLogger(__name__)


def monitor_devices() -> None:
    from app.api.v1.routes.sessions import _stop_edges_for_session, session_control_lock
    with SessionLocal() as db:
        with device_state_lock:
            for camera in db.scalars(select(CameraNode).where(CameraNode.owner_user_id.is_not(None))):
                refresh_camera(camera)
            db.commit()
        for session in db.scalars(select(Session).where(Session.status.in_(["preparing", "running", "stopping"]))):
            if not session_control_lock.acquire(blocking=False):
                continue
            try:
                db.refresh(session)
                now = datetime.now(UTC)
                metadata = dict(session.metadata_json or {})
                if session.status == "preparing":
                    started = datetime.fromisoformat(metadata.get("preparing_at") or now.isoformat())
                    if now - started > timedelta(seconds=35):
                        session.status = "stopping"
                        session.stopped_at = now
                        metadata["stop_requested_at"] = now.isoformat()
                        session.metadata_json = metadata
                if session.status == "running":
                    with recording_write_lock:
                        process_presence_timeouts(db, session, now)
                        db.commit()
                    renewed = []
                    operator = datetime.fromisoformat(metadata.get("operator_last_seen") or metadata.get("lease_confirmed_at") or now.isoformat())
                    if now - operator > timedelta(seconds=20):
                        session.status = "stopping"
                        session.stopped_at = now
                        metadata["stop_requested_at"] = now.isoformat()
                    for cam_id, run_id in metadata.get("edge_runs", {}).items():
                        if session.status != "running":
                            break
                        camera = db.scalar(select(CameraNode).where(CameraNode.cam_id == cam_id))
                        try:
                            health = (camera.metadata_json or {}).get("health", {}) if camera else {}
                            if not health.get("ready"):
                                raise ValueError("No recent inference frame")
                            edge_request(camera, "POST", "/detection/lease", timeout=1.2,
                                         json={"session_id": session.session_code, "run_id": run_id})
                            renewed.append(cam_id)
                        except Exception:
                            logger.warning("Device lease renewal failed for %s", cam_id)
                    if renewed and len(renewed) == len(metadata.get("edge_runs", {})):
                        metadata["lease_confirmed_at"] = now.isoformat()
                    last = datetime.fromisoformat(metadata.get("lease_confirmed_at") or now.isoformat())
                    if now - last > timedelta(seconds=30):
                        session.status = "stopping"
                        session.stopped_at = now
                        metadata["stop_requested_at"] = now.isoformat()
                    session.metadata_json = metadata
                if session.status == "stopping":
                    owner = db.get(User, session.owner_user_id)
                    results = _stop_edges_for_session(session, owner, db)
                    last = datetime.fromisoformat(metadata.get("lease_confirmed_at") or metadata.get("stop_requested_at") or now.isoformat())
                    if all(r["status"] == "stopped" for r in results) or now - last > timedelta(seconds=35):
                        from app.services.event_engine import resolve_active_events_for_session
                        resolve_active_events_for_session(db, session, session.stopped_at or now)
                        session.status = "review_pending"
                db.commit()
            finally:
                session_control_lock.release()
