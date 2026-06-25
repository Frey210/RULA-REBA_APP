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
    updated_at: datetime
    image_url: str
