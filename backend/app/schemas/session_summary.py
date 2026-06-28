from datetime import datetime

from pydantic import BaseModel


class ScoreAggregate(BaseModel):
    average: float | None
    peak: int | None
    samples: int


class WorkerExposureSummary(BaseModel):
    session_worker_id: str
    worker_id: str | None
    worker_name: str | None
    employee_number: str | None
    edge_worker_id: str
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    detection_count: int
    high_risk_event_count: int
    sustained_event_count: int
    high_risk_duration_ms: int
    reviewed_event_count: int
    rula: ScoreAggregate
    reba: ScoreAggregate


class SessionExposureSummary(BaseModel):
    session_id: str
    worker_count: int
    event_count: int
    high_risk_event_count: int
    sustained_event_count: int
    high_risk_duration_ms: int
    reviewed_event_count: int
    workers: list[WorkerExposureSummary]
