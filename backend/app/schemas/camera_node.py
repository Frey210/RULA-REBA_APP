from datetime import datetime

from pydantic import BaseModel, Field


class CameraNodeCreate(BaseModel):
    cam_id: str
    hostname: str | None = None
    device_type: str | None = None
    metadata: dict = Field(default_factory=dict)


class CameraNodeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    edge_base_url: str | None = Field(default=None, max_length=500)


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
