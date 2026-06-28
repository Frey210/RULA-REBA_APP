from datetime import datetime

from pydantic import BaseModel


class ErgonomicEventRead(BaseModel):
    id: str
    session_id: str
    camera_node_id: str
    session_worker_id: str
    worker_id: str | None
    worker_name: str | None
    employee_number: str | None
    edge_worker_id: str
    event_type: str
    status: str
    severity: str
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    score_type: str | None
    score: int | None
    risk_level: str | None
    confidence: float | None
    metadata_json: dict
    reviewed_assessment_types: list[str]
