from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    camera_node_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class SessionRead(BaseModel):
    id: str
    session_code: str
    status: str
    started_at: datetime | None
    stopped_at: datetime | None
    completed_at: datetime | None
    notes: str | None
    metadata_json: dict

    model_config = {"from_attributes": True}


class SessionWorkerAssign(BaseModel):
    worker_id: str | None = None


class SessionWorkerRead(BaseModel):
    id: str
    session_id: str
    worker_id: str | None
    worker_name: str | None = None
    employee_number: str | None = None
    edge_worker_id: str
    tracking_id: int | None
    identity_status: str
    reid_confidence: float | None
    confirmed_at: datetime | None
