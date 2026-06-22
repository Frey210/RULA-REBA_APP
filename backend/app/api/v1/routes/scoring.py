from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.scoring import ScorePreviewRequest, ScorePreviewResponse
from app.services.scoring import calculate_score

router = APIRouter()


@router.post("/preview", response_model=ScorePreviewResponse)
def preview_score(
    payload: ScorePreviewRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return calculate_score(payload.assessment_type, payload.angles, payload.manual)

