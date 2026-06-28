from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.report import Report
from app.models.session import Session
from app.models.user import User
from app.schemas.report import ReportCreateResponse, ReportRead
from app.services.event_engine import backfill_session_events
from app.services.report_generation import generate_session_pdf_report

router = APIRouter()


@router.get("", response_model=list[ReportRead])
def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[ReportRead]:
    reports = db.scalars(
        select(Report)
        .where(Report.owner_user_id == current_user.id)
        .order_by(Report.generated_at.desc(), Report.created_at.desc())
    )
    return [_report_read(report) for report in reports]


@router.post("/sessions/{session_id}", response_model=ReportCreateResponse)
def create_session_report(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> ReportRead:
    session = db.get(Session, session_id)
    if session is None or session.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop the running session before generating a report",
        )
    backfill_session_events(db, session)
    report = generate_session_pdf_report(db, session, current_user)
    return _report_read(report)


@router.get("/{report_id}/content")
def download_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> FileResponse:
    report = db.get(Report, report_id)
    if report is None or report.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not report.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")
    path = Path(report.file_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")
    filename = path.name
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        headers={"Cache-Control": "private, max-age=60"},
    )


def _report_read(report: Report) -> ReportRead:
    return ReportRead(
        id=report.id,
        session_id=report.session_id,
        report_type=report.report_type,
        status=report.status,
        generated_by=report.generated_by,
        generated_at=report.generated_at,
        metadata_json=report.metadata_json,
        download_url=f"/api/v1/reports/{report.id}/content" if report.status == "ready" else None,
    )
