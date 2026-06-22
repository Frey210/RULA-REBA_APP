from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.camera_node import CameraNode
from app.models.user import User
from app.schemas.camera_node import CameraNodeRead

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

