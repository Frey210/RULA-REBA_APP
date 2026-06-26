from datetime import datetime
from typing import Literal

from pydantic import BaseModel


EnrollmentView = Literal["front", "left", "right"]


class WorkerEnrollmentImageRead(BaseModel):
    id: str
    worker_id: str
    view: EnrollmentView
    content_type: str
    file_size: int
    width: int
    height: int
    quality_status: str
    quality_details: dict[str, object]
    updated_at: datetime
    image_url: str
