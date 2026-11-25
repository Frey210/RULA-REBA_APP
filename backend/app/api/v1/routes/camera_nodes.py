from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from types import SimpleNamespace

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.camera_node import CameraNode
from app.models.user import User
from app.schemas.camera_node import CameraNodeRead, CameraNodeUpdate, CameraReconnect, EthernetModeRequest
from app.services.edge_devices import camera_is_fresh, edge_request, owned_camera, device_state_lock, backend_url_for_edge, refresh_camera

router = APIRouter()


def require_network_idle(camera, db):
    from app.models.session import Session as AssessmentSession
    for session in db.scalars(select(AssessmentSession).where(AssessmentSession.status.in_(['preparing', 'running', 'stopping']))):
        if camera.cam_id in (session.metadata_json or {}).get('camera_node_ids', []):
            raise HTTPException(409, 'Stop the session before changing its camera network')


@router.post('/{camera_node_id}/reconnect', response_model=CameraNodeRead)
def reconnect_camera(camera_node_id: str, payload: CameraReconnect,
                     current_user: Annotated[User, Depends(get_current_user)],
                     db: Annotated[Session, Depends(get_db)]) -> CameraNode:
    with device_state_lock:
        camera = owned_camera(db, camera_node_id, current_user.id)
        require_network_idle(camera, db)
        metadata = {**(camera.metadata_json or {}), 'edge_base_url': payload.edge_base_url}
        candidate = SimpleNamespace(id=camera.id, cam_id=camera.cam_id, owner_user_id=camera.owner_user_id,
                                    node_credential_hash=camera.node_credential_hash, metadata_json=metadata)
        try:
            info = edge_request(candidate, 'GET', '/stream/status', timeout=3).json()
            if info.get('cam_id') != camera.cam_id:
                raise ValueError('Camera identity mismatch')
            backend = backend_url_for_edge(payload.edge_base_url)
            result = edge_request(candidate, 'POST', '/network/reconnect', timeout=8,
                                  json={'backend_url': backend}).json()
            if result.get('device_id') != metadata.get('device_id') or result.get('status') != 'connected':
                raise ValueError('Reconnect identity mismatch')
        except (httpx.HTTPError, ValueError, OSError) as exc:
            raise HTTPException(409, 'Cannot verify both connection directions. Update the Pi agent, check the owning app and allow its backend on port 8000.') from exc
        metadata['backend_url'] = backend
        camera.metadata_json = metadata
        refresh_camera(camera)
        db.commit()
        db.refresh(camera)
        return camera


@router.post('/{camera_node_id}/network/ethernet', status_code=202)
def camera_ethernet(camera_node_id: str, payload: EthernetModeRequest,
                    current_user: Annotated[User, Depends(get_current_user)],
                    db: Annotated[Session, Depends(get_db)]) -> dict:
    with device_state_lock:
        camera = owned_camera(db, camera_node_id, current_user.id)
        require_network_idle(camera, db)
        try:
            return edge_request(camera, 'POST', '/network/ethernet', json=payload.model_dump(), timeout=5).json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(409, 'Network change was not confirmed. Check the Pi network status; it may still be switching or require an agent update.') from exc


@router.post('/{camera_node_id}/network/ethernet/confirm')
def camera_ethernet_confirm(camera_node_id: str, current_user: Annotated[User, Depends(get_current_user)],
                            db: Annotated[Session, Depends(get_db)]) -> dict:
    camera = owned_camera(db, camera_node_id, current_user.id)
    require_network_idle(camera, db)
    try:
        return edge_request(camera, 'POST', '/network/ethernet/confirm', timeout=5).json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(409, 'Use Scan LAN or Probe IP to reconnect through the new Ethernet address before keeping this mode.') from exc


@router.get("", response_model=list[CameraNodeRead])
def list_camera_nodes(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CameraNode]:
    cameras = list(
        db.scalars(
            select(CameraNode)
            .where(CameraNode.owner_user_id == current_user.id)
            .order_by(CameraNode.created_at.desc())
        )
    )
    for camera in cameras:
        if camera.status == "online" and not camera_is_fresh(camera):
            camera.status = "offline"
    return cameras


@router.patch("/{camera_node_id}", response_model=CameraNodeRead)
def update_camera_node(
    camera_node_id: str,
    payload: CameraNodeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CameraNode:
    with device_state_lock:
        return _update_camera_node(camera_node_id, payload, current_user, db)


def _update_camera_node(camera_node_id, payload, current_user, db):
    camera = db.scalar(
        select(CameraNode).where(
            CameraNode.id == camera_node_id,
            CameraNode.owner_user_id == current_user.id,
        )
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera node not found")

    metadata = dict(camera.metadata_json or {})
    if payload.display_name is not None:
        metadata["display_name"] = payload.display_name.strip()
    if payload.edge_base_url is not None:
        metadata["edge_base_url"] = payload.edge_base_url.rstrip("/")
    camera.metadata_json = metadata
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/{camera_node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera_node(
    camera_node_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    with device_state_lock:
        return _delete_camera_node(camera_node_id, current_user, db)


def _delete_camera_node(camera_node_id, current_user, db):
    camera = db.scalar(
        select(CameraNode).where(
            CameraNode.id == camera_node_id,
            CameraNode.owner_user_id == current_user.id,
        )
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera node not found")

    from app.models.session import Session as AssessmentSession
    for session in db.scalars(select(AssessmentSession).where(AssessmentSession.status.in_(["running", "preparing", "stopping"]))):
        if camera.cam_id in (session.metadata_json or {}).get("camera_node_ids", []):
            raise HTTPException(409, "Stop the session before removing its camera")

    metadata = dict(camera.metadata_json or {})
    metadata["removed_from_user_at"] = camera.updated_at.isoformat() if camera.updated_at else None
    camera.owner_user_id = None
    camera.status = "offline"
    camera.paired_at = None
    camera.node_credential_hash = None
    camera.metadata_json = metadata
    db.add(camera)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{camera_node_id}/frame")
def camera_frame(camera_node_id: str, current_user: Annotated[User, Depends(get_current_user)],
                 db: Annotated[Session, Depends(get_db)], overlay: bool = True) -> Response:
    camera = owned_camera(db, camera_node_id, current_user.id)
    try:
        response = edge_request(camera, "GET", "/snapshot/latest", timeout=2,
                                params={"overlay": str(overlay).lower()})
        if response.headers.get("content-type", "").split(";")[0] != "image/jpeg":
            raise ValueError("Camera did not return a frame")
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Camera unavailable. Check its connection or run Scan LAN.") from exc
    return Response(response.content, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/{camera_node_id}/network/{action}")
def camera_network(camera_node_id: str, action: str,
                   current_user: Annotated[User, Depends(get_current_user)],
                   db: Annotated[Session, Depends(get_db)]) -> dict:
    if action not in {"status", "wifi"}:
        raise HTTPException(404, "Unknown network action")
    camera = owned_camera(db, camera_node_id, current_user.id)
    try:
        return edge_request(camera, "GET", f"/network/{action}", timeout=40).json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Cannot reach this device. Run Scan LAN.") from exc


@router.post("/{camera_node_id}/network/wifi/connect", status_code=202)
def camera_wifi_connect(camera_node_id: str, payload: dict,
                        current_user: Annotated[User, Depends(get_current_user)],
                        db: Annotated[Session, Depends(get_db)]) -> dict:
    camera = owned_camera(db, camera_node_id, current_user.id)
    require_network_idle(camera, db)
    try:
        return edge_request(camera, "POST", "/network/wifi/connect", json=payload).json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Wi-Fi setup failed. Check the device connection and try again.") from exc
