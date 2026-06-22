from datetime import datetime

from pydantic import BaseModel, Field


class CameraNodeCreate(BaseModel):
    cam_id: str
    hostname: str | None = None
    device_type: str | None = None
    metadata: dict = Field(default_factory=dict)


class CameraNodeUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


class CameraNodeRead(BaseModel):
    id: str
    cam_id: str
    hostname: str | None
    device_type: str | None
    status: str
    last_seen_at: datetime | None
    paired_at: datetime | None
    metadata_json: dict

    model_config = {"from_attributes": True}
