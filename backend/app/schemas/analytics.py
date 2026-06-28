from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.session_summary import ScoreAggregate


class RiskWorkerRow(BaseModel):
    worker_key: str
    worker_id: str | None
    worker_name: str
    employee_number: str | None
    session_count: int
    high_risk_event_count: int
    high_risk_duration_ms: int
    sustained_event_count: int
    rula: ScoreAggregate
    reba: ScoreAggregate


class RiskSessionRow(BaseModel):
    session_id: str
    session_code: str
    notes: str | None
    status: str
    started_at: datetime | None
    worker_count: int
    high_risk_event_count: int
    high_risk_duration_ms: int
    peak_rula: int | None
    peak_reba: int | None


class DailyExposureRow(BaseModel):
    day: date
    session_count: int
    worker_count: int
    high_risk_event_count: int
    high_risk_duration_ms: int
    peak_rula: int | None
    peak_reba: int | None


class WorstEventRow(BaseModel):
    event_id: str
    session_id: str
    session_code: str
    session_worker_id: str
    worker_name: str
    event_type: str
    started_at: datetime
    duration_ms: int
    score_type: str | None
    score: int | None
    risk_level: str | None
    severity: str
    reviewed: bool


class ExposureOverview(BaseModel):
    period_days: int
    session_count: int
    completed_session_count: int
    worker_count: int
    high_risk_event_count: int
    sustained_event_count: int
    high_risk_duration_ms: int
    reviewed_assessment_count: int
    rula: ScoreAggregate
    reba: ScoreAggregate
    top_workers: list[RiskWorkerRow]
    top_sessions: list[RiskSessionRow]
    daily_trend: list[DailyExposureRow]
    worst_events: list[WorstEventRow]
