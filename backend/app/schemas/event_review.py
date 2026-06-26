from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EventReviewUpsert(BaseModel):
    load_score: int = Field(default=0, ge=0, le=3)
    coupling_score: int | None = Field(default=None, ge=0, le=3)
    activity_score: int = Field(default=0, ge=0, le=2)
    wrist_twist_score: int | None = Field(default=None, ge=1, le=2)
    notes: str | None = Field(default=None, max_length=2000)

class EventReviewRead(BaseModel):
    id: str
    assessment_type: Literal["rula", "reba"]
    assessment_status: str
    provisional_score: int | None
    provisional_risk_level: str | None
    score: int
    risk_level: str
    manual_inputs: dict[str, int]
    breakdown: dict
    notes: str | None
    reviewed_by: str | None
    calculated_at: datetime


class EventSnapshotRead(BaseModel):
    id: str
    snapshot_type: str
    captured_at: datetime
    content_url: str
    metadata: dict


class EventDetailRead(BaseModel):
    id: str
    angles: dict
    assessment_quality: dict
    provisional_scores: dict
    reviews: list[EventReviewRead]
    snapshots: list[EventSnapshotRead]
