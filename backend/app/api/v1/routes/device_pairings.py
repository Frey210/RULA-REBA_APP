from datetime import UTC, datetime, timedelta
from random import SystemRandom
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.camera_node import CameraNode
from app.models.device_pairing import DevicePairing
from app.models.user import User
from app.schemas.device_pairing import PairingComplete, PairingCompleteRead, PairingTokenRead

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
    if camera is None:
        camera = CameraNode(cam_id=payload.cam_id)
        db.add(camera)
        db.flush()

    camera.owner_user_id = pairing.owner_user_id
    camera.hostname = payload.hostname
    camera.device_type = payload.device_type
    camera.status = "online"
    camera.last_seen_at = now
    camera.paired_at = now
    camera.metadata_json = payload.metadata

    pairing.camera_node_id = camera.id
    pairing.status = "paired"
    pairing.paired_at = now
    db.commit()
    db.refresh(camera)
    return PairingCompleteRead(camera_node_id=camera.id, cam_id=camera.cam_id, status="paired")
