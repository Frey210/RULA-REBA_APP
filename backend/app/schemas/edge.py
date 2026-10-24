from typing import Literal

from pydantic import BaseModel, Field, field_validator
import math


class Keypoint(BaseModel):
    id: int
    name: str | None = None
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    score: float | None = Field(default=None, ge=0, le=1)


class KeypointsPayload(BaseModel):
    format: str = "coco17"
    points: list[Keypoint] = Field(default_factory=list, max_length=128)


class EdgeDetection(BaseModel):
    worker_id: str
    tracking_id: int
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    reid_confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    bbox: list[float] = Field(min_length=4, max_length=4)
    keypoints: KeypointsPayload
    snapshot_path: str | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("bbox")
    @classmethod
    def valid_bbox(cls, value):
        if not all(math.isfinite(item) for item in value) or value[2] <= 0 or value[3] <= 0:
            raise ValueError("Bounding box must be finite with positive dimensions")
        return value


class EdgeDetectionEvent(BaseModel):
    schema_version: str = "1.0"
    event_type: Literal["detection"]
    cam_id: str
    session_id: str
    timestamp: int
    frame_id: int = Field(ge=0)
    run_id: str = Field(min_length=1, max_length=36)
    clock_source: Literal["device_clock", "backend_session_clock"] = "device_clock"
    detections: list[EdgeDetection] = Field(default_factory=list, max_length=32)


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

