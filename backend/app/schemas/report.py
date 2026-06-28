from datetime import datetime

from pydantic import BaseModel


class ReportRead(BaseModel):
    id: str
    session_id: str | None
    report_type: str
    status: str
    generated_by: str | None
    generated_at: datetime | None
    metadata_json: dict
    download_url: str | None = None


class ReportCreateResponse(ReportRead):
    pass
