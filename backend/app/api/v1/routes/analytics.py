from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import ExposureOverview
from app.services.exposure_analytics import build_exposure_overview

router = APIRouter()


@router.get("/overview", response_model=ExposureOverview)
def exposure_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> ExposureOverview:
    return build_exposure_overview(db, current_user.id, days)
