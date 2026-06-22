from datetime import datetime

from pydantic import BaseModel, Field


class PairingTokenRead(BaseModel):
    pairing_id: str
    pairing_code: str
    expires_at: datetime


class PairingComplete(BaseModel):
    pairing_code: str
    cam_id: str
    hostname: str | None = None
    device_type: str = "raspberry_pi_5_hailo8"
    metadata: dict = Field(default_factory=dict)


class PairingCompleteRead(BaseModel):
    camera_node_id: str
    cam_id: str
    status: str

