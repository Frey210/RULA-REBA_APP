from typing import Literal

from pydantic import BaseModel, Field


class Keypoint(BaseModel):
    id: int
    name: str | None = None
    x: float
    y: float
    score: float | None = None


class KeypointsPayload(BaseModel):
    format: str = "coco17"
    points: list[Keypoint] = Field(default_factory=list)


class EdgeDetection(BaseModel):
    worker_id: str
    tracking_id: int
    confidence: float | None = None
    reid_confidence: float | None = None
    bbox: list[float] = Field(min_length=4, max_length=4)
    keypoints: KeypointsPayload
    snapshot_path: str | None = None
    metadata: dict = Field(default_factory=dict)


class EdgeDetectionEvent(BaseModel):
    schema_version: str = "1.0"
    event_type: Literal["detection"]
    cam_id: str
    session_id: str
    timestamp: int
    frame_id: int
    detections: list[EdgeDetection] = Field(default_factory=list)


class EdgeHeartbeatEvent(BaseModel):
    schema_version: str = "1.0"
    event_type: Literal["heartbeat"]
    cam_id: str
    timestamp: int
    status: str = "online"
    metrics: dict = Field(default_factory=dict)


class WebSocketAck(BaseModel):
    schema_version: str = "1.0"
    event_type: Literal["ack"] = "ack"
    status: str = "accepted"


class WebSocketError(BaseModel):
    schema_version: str = "1.0"
    event_type: Literal["error"] = "error"
    code: str
    detail: str

