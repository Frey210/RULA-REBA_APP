from datetime import UTC, datetime, timedelta
from json import JSONDecodeError
from random import SystemRandom
from typing import Annotated
from uuid import UUID
import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.camera_node import CameraNode
from app.models.device_pairing import DevicePairing
from app.models.user import User
from app.schemas.device_pairing import PairingComplete, PairingCompleteRead, PairingTokenRead, PairingRelay
from app.services.edge_devices import issue_device_token, validate_edge_url, device_token, device_state_lock, edge_http

router = APIRouter()
random = SystemRandom()


@router.post("", response_model=PairingTokenRead, status_code=status.HTTP_201_CREATED)
def create_pairing(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PairingTokenRead:
    pairing_code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    pairing = DevicePairing(
        owner_user_id=current_user.id,
        pairing_code_hash=hash_password(pairing_code),
        expires_at=expires_at,
    )
    db.add(pairing)
    db.commit()
    db.refresh(pairing)
    return PairingTokenRead(
        pairing_id=pairing.id,
        pairing_code=pairing_code,
        expires_at=expires_at,
    )


@router.post("/complete", response_model=PairingCompleteRead)
def complete_pairing(
    payload: PairingComplete,
    db: Annotated[Session, Depends(get_db)],
) -> PairingCompleteRead:
    with device_state_lock:
        return _complete_pairing(payload, db)


def _complete_pairing(payload: PairingComplete, db: Session) -> PairingCompleteRead:
    now = datetime.now(UTC)
    candidates = db.scalars(
        select(DevicePairing).where(
            DevicePairing.status == "pending",
            DevicePairing.expires_at > now,
        )
    ).all()
    pairing = next(
        (candidate for candidate in candidates if verify_password(payload.pairing_code, candidate.pairing_code_hash)),
        None,
    )
    if pairing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing code not found")

    camera = db.scalar(select(CameraNode).where(CameraNode.cam_id == payload.cam_id))
    if camera and camera.owner_user_id and camera.owner_user_id != pairing.owner_user_id:
        raise HTTPException(409, "This device belongs to another account")
    if camera and (camera.metadata_json or {}).get("device_id") not in {None, str(payload.device_id)}:
        raise HTTPException(409, "A different device already uses this camera ID")
    try:
        edge_url = validate_edge_url(str(payload.metadata.get("edge_base_url") or ""))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if camera is None:
        camera = CameraNode(cam_id=payload.cam_id)
        db.add(camera)
        db.flush()

    camera.owner_user_id = pairing.owner_user_id
    camera.hostname = payload.hostname
    camera.device_type = payload.device_type
    camera.status = "checking"
    camera.paired_at = now
    camera.metadata_json = {
        "display_name": (camera.metadata_json or {}).get("display_name") or payload.hostname or payload.cam_id,
        "device_id": str(payload.device_id), "edge_base_url": edge_url,
    }
    token = issue_device_token(camera)

    pairing.camera_node_id = camera.id
    pairing.status = "paired"
    pairing.paired_at = now
    db.commit()
    db.refresh(camera)
    return PairingCompleteRead(camera_node_id=camera.id, cam_id=camera.cam_id, status="paired", device_token=token)


@router.post("/relay")
def relay_pairing(payload: PairingRelay, current_user: Annotated[User, Depends(get_current_user)],
                  db: Annotated[Session, Depends(get_db)]) -> dict:
    camera = db.scalar(select(CameraNode).where(CameraNode.cam_id == payload.cam_id))
    if camera and camera.owner_user_id not in {None, current_user.id}:
        raise HTTPException(403, "This device belongs to another account")
    try:
        address = validate_edge_url(payload.edge_base_url)
        backend = validate_edge_url(payload.backend_url)
        discovery = edge_http.get(address + "/pairing/info", timeout=2)
        discovery.raise_for_status()
        info = discovery.json()
        if not isinstance(info, dict) or info.get("service") != "ergoquipt-edge":
            raise ValueError("This address is not an ERGoSIGHT camera")
        if info.get("cam_id") != payload.cam_id:
            raise ValueError("A different camera is using this address")
        try:
            UUID(str(info.get("device_id")))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(409, "Camera software is outdated. Update the Raspberry Pi edge agent to 0.2.0 "
                                "or newer, restart its service, then Scan LAN and pair again. "
                                "Do not delete your camera or recordings.") from exc
        if camera and (camera.metadata_json or {}).get("device_id") not in {None, info.get("device_id")}:
            raise ValueError("Device identity changed. Check the connected camera")
        headers = ({"Authorization": f"Bearer {device_token(camera)}"}
                   if camera and camera.node_credential_hash and (camera.metadata_json or {}).get("credential_nonce") else {})
        response = edge_http.post(address + "/pairing/complete", headers=headers, timeout=15, json={
            "pairing_code": payload.pairing_code, "backend_url": backend, "edge_base_url": address,
        })
        response.raise_for_status()
        result = response.json()
        return {"status": result["status"], "cam_id": result["cam_id"]}
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 403:
            detail = "Camera rejected this backend's credential. Use the original owning backend; do not reset device state."
        elif code == 404:
            detail = "Pairing code was not found or expired. Create a new code and pair again."
        elif code == 409:
            detail = "Camera account or identity conflicts with an existing device. Check the owning account and camera ID."
        elif code == 422:
            detail = "Camera and backend pairing formats do not match. Update both to 0.2.0 or newer."
        else:
            detail = "Camera could not complete pairing. Check that its Backend URL reaches this laptop and port 8000 is allowed by the firewall."
        raise HTTPException(409, detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(503, "Camera did not respond. Check its power and LAN connection, then run Scan LAN.") from exc
    except (JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(409, "Camera returned an invalid pairing response. Update its edge agent and retry.") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
