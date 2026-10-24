import hashlib
import hmac
import secrets
import threading
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.models.camera_node import CameraNode
from app.models.user import User

device_state_lock = threading.RLock()
edge_http = httpx.Client(trust_env=False, limits=httpx.Limits(max_connections=12, max_keepalive_connections=8))


def validate_edge_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Enter an HTTP device address without credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Device address must not contain a path or query")
    return value.rstrip("/")


def device_token(camera: CameraNode) -> str:
    nonce = (camera.metadata_json or {}).get("credential_nonce")
    if not nonce or not camera.node_credential_hash:
        raise ValueError("Pair this device again to enable secure communication")
    message = f"edge:{camera.id}:{camera.owner_user_id}:{nonce}".encode()
    return hmac.new(settings.jwt_secret_key.encode(), message, hashlib.sha256).hexdigest()


def issue_device_token(camera: CameraNode) -> str:
    camera.metadata_json = {**(camera.metadata_json or {}), "credential_nonce": secrets.token_hex(24)}
    camera.node_credential_hash = "pending"
    token = device_token(camera)
    camera.node_credential_hash = hashlib.sha256(token.encode()).hexdigest()
    return token


def authenticate_device(db, cam_id: str, authorization: str | None) -> CameraNode:
    camera = db.scalar(select(CameraNode).where(CameraNode.cam_id == cam_id))
    token = (authorization or "").removeprefix("Bearer ")
    if (camera is None or not camera.owner_user_id or not camera.node_credential_hash
            or not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), camera.node_credential_hash)):
        raise ValueError("Device authentication failed; pair the device again")
    user = db.get(User, camera.owner_user_id)
    if user is None or not user.is_active:
        raise ValueError("Device owner is inactive")
    return camera


def edge_request(camera: CameraNode, method: str, path: str, *, timeout: float = 3, **kwargs) -> httpx.Response:
    address = validate_edge_url(str((camera.metadata_json or {}).get("edge_base_url") or ""))
    response = edge_http.request(method, address + path, headers={"Authorization": f"Bearer {device_token(camera)}"},
                             timeout=timeout, **kwargs)
    response.raise_for_status()
    if response.headers.get("x-device-id") != (camera.metadata_json or {}).get("device_id"):
        raise ValueError("A different device is using this address. Run Scan LAN")
    return response


def refresh_camera(camera: CameraNode) -> None:
    metadata = dict(camera.metadata_json or {})
    try:
        state = edge_request(camera, "GET", "/stream/status", timeout=1.2).json()
        if state.get("cam_id") != camera.cam_id:
            raise ValueError("Device identity mismatch. Run Scan LAN")
        camera.last_seen_at = datetime.now(UTC)
        camera.status = "online"
        metadata["health"] = {key: state.get(key) for key in
                              ("camera_available", "running", "ready", "session_id", "run_id", "frame_age_ms", "detail")}
        metadata["connection_error"] = None
    except (httpx.HTTPError, ValueError):
        camera.status = "offline" if camera.node_credential_hash else "pairing_required"
        metadata["health"] = {"camera_available": False, "running": False}
        metadata["connection_error"] = "Device unavailable or identity changed. Check its cable and run Scan LAN."
    camera.metadata_json = metadata


def camera_is_fresh(camera: CameraNode) -> bool:
    seen = camera.last_seen_at
    if seen and seen.tzinfo is None:
        seen = seen.replace(tzinfo=UTC)
    return bool(camera.status == "online" and seen and datetime.now(UTC) - seen < timedelta(seconds=10))


def owned_camera(db, camera_id: str, user_id: str) -> CameraNode:
    camera = db.get(CameraNode, camera_id)
    if camera is None or camera.owner_user_id != user_id:
        raise HTTPException(404, "Camera not found")
    return camera
