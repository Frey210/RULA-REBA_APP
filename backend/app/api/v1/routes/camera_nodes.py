from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.camera_node import CameraNode
from app.models.user import User
from app.schemas.camera_node import CameraNodeRead, CameraNodeUpdate

router = APIRouter()


@router.get("", response_model=list[CameraNodeRead])
def list_camera_nodes(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CameraNode]:
    return list(
        db.scalars(
            select(CameraNode)
            .where(CameraNode.owner_user_id == current_user.id)
            .order_by(CameraNode.created_at.desc())
        )
    )


@router.patch("/{camera_node_id}", response_model=CameraNodeRead)
def update_camera_node(
    camera_node_id: str,
    payload: CameraNodeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CameraNode:
    camera = db.scalar(
        select(CameraNode).where(
            CameraNode.id == camera_node_id,
            CameraNode.owner_user_id == current_user.id,
        )
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera node not found")

    metadata = dict(camera.metadata_json or {})
    metadata["display_name"] = payload.display_name.strip()
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
    camera = db.scalar(
        select(CameraNode).where(
            CameraNode.id == camera_node_id,
            CameraNode.owner_user_id == current_user.id,
        )
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera node not found")

    metadata = dict(camera.metadata_json or {})
    metadata["removed_from_user_at"] = camera.updated_at.isoformat() if camera.updated_at else None
    camera.owner_user_id = None
    camera.status = "offline"
    camera.paired_at = None
    camera.metadata_json = metadata
    db.add(camera)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
