from typing import Literal

from pydantic import BaseModel, Field


class ScorePreviewRequest(BaseModel):
    assessment_type: Literal["rula", "reba"]
    angles: dict[str, float | int] = Field(default_factory=dict)
    manual: dict[str, float | int] = Field(default_factory=dict)


class ScorePreviewResponse(BaseModel):
    assessment_type: Literal["rula", "reba"]
    score: int
    risk_level: str
    breakdown: dict[str, int]

