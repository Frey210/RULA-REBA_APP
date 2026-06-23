from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.camera_node import CameraNode
from app.models.session import Session
from app.models.user import User
from app.schemas.session import SessionCreate, SessionRead
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
    session.status = "review_pending"
    session.stopped_at = datetime.now(UTC)
    session.metadata_json = {
        **(session.metadata_json or {}),
        "edge_stop_results": edge_results,
    }
    db.commit()
    db.refresh(session)
    return session


def _get_owned_session(session_id: str, current_user: User, db: DbSession) -> Session:
    session = db.get(Session, session_id)
    if session is None or session.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


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
