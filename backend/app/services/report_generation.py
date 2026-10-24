import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab
from reportlab.platypus import Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.models.assessment import Assessment
from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.ergonomic_event import ErgonomicEvent
from app.models.report import Report
from app.models.session import Session
from app.models.session_worker import SessionWorker
from app.models.snapshot import Snapshot
from app.models.user import User
from app.models.worker import Worker
from app.models.worker_enrollment_image import WorkerEnrollmentImage
from app.services.exposure_intervals import merged_duration_ms
from app.services.pose_quality import REQUIRED_COMPONENTS


def media_path(value: str) -> Path:
    path = Path(value).resolve()
    if not path.is_relative_to(settings.media_root.resolve()) or not path.is_file():
        raise ValueError("Media file unavailable")
    return path


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _csv(rows, columns, *, header=True) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output)
    if header:
        writer.writerow(columns)
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column)
            if isinstance(value, (dict, list)):
                value = _json(value)
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return output.getvalue()


def _angle_rows(detection):
    return [[name, (detection.angles or {}).get(name)] for name in REQUIRED_COMPONENTS]


def generate_session_pdf_report(db: DbSession, session: Session, current_user: User) -> Report:
    report_id = str(uuid4())
    now = datetime.now(UTC)
    report_dir = settings.media_root / "reports" / current_user.id / session.id / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    output_path = report_dir / "ergonomic_report.pdf"
    archive_path = report_dir / "session_documentation.zip"
    workers = db.execute(select(SessionWorker, Worker).outerjoin(Worker, SessionWorker.worker_id == Worker.id)
                         .where(SessionWorker.session_id == session.id).order_by(SessionWorker.created_at)).all()
    events = list(db.scalars(select(ErgonomicEvent).where(ErgonomicEvent.session_id == session.id,
        ErgonomicEvent.event_type.notin_(["worker_entered", "worker_left"])).order_by(ErgonomicEvent.started_at)))
    assessments = list(db.scalars(select(Assessment).where(Assessment.session_id == session.id)
                                 .order_by(Assessment.calculated_at)))
    snapshots = list(db.scalars(select(Snapshot).where(Snapshot.session_id == session.id)
                               .order_by(Snapshot.captured_at)))
    detections = {row.id: row for row in db.scalars(select(Detection).where(
        Detection.id.in_({event.source_detection_id for event in events if event.source_detection_id} |
                         {snapshot.detection_id for snapshot in snapshots if snapshot.detection_id})))}
    camera_ids = {row.camera_node_id for row, _ in workers} | {event.camera_node_id for event in events}
    selected_ids = (session.metadata_json or {}).get("camera_node_ids", [])
    cameras = list(db.scalars(select(CameraNode).where(CameraNode.owner_user_id == current_user.id,
        (CameraNode.id.in_(camera_ids)) | (CameraNode.cam_id.in_(selected_ids)))))
    camera_data = [dict(id=c.id, cam_id=c.cam_id, hostname=c.hostname, device_type=c.device_type,
                        device_id=(c.metadata_json or {}).get("device_id")) for c in cameras]
    worker_data = [dict(id=row.id, worker_id=row.worker_id, name=worker.name if worker else row.edge_worker_id,
        employee_number=worker.employee_number if worker else None,
        department=worker.department if worker else None, position=worker.position if worker else None,
        camera_node_id=row.camera_node_id, run_id=row.run_id, edge_worker_id=row.edge_worker_id,
        identity_status=row.identity_status, confirmed_at=_format_dt(row.confirmed_at)) for row, worker in workers]
    event_data = [dict(id=e.id, session_worker_id=e.session_worker_id, camera_node_id=e.camera_node_id,
        event_type=e.event_type, status=e.status, severity=e.severity, started_at=_format_dt(e.started_at),
        ended_at=_format_dt(e.ended_at), duration_ms=e.duration_ms, score_type=e.score_type,
        score=e.score, risk_level=e.risk_level, source_detection_id=e.source_detection_id,
        last_detection_id=e.last_detection_id, confidence=e.confidence) for e in events]
    assessment_data = [dict(id=a.id, session_worker_id=a.session_worker_id, event_id=a.ergonomic_event_id,
        type=a.assessment_type, status=a.assessment_status, score=a.score, risk_level=a.risk_level,
        provisional_score=a.provisional_score, provisional_risk_level=a.provisional_risk_level,
        score_a=a.score_a, score_b=a.score_b, breakdown=a.breakdown, review_notes=a.review_notes,
        source_detection_ids=a.source_detection_ids, calculated_at=_format_dt(a.calculated_at)) for a in assessments]
    evidence = [dict(id=s.id, event_id=s.ergonomic_event_id, detection_id=s.detection_id,
        camera_node_id=s.camera_node_id, session_worker_id=s.session_worker_id, kind=s.snapshot_type,
        captured_at=_format_dt(s.captured_at), source=s.metadata_json.get("source", "legacy"),
        run_id=s.metadata_json.get("run_id"), frame_id=s.metadata_json.get("frame_id"),
        expected_sha256=s.metadata_json.get("checksum_sha256"), _path=s.file_path,
        status=s.metadata_json.get("status", "legacy")) for s in snapshots]
    registered_ids = {worker.id for _, worker in workers if worker and worker.owner_user_id == current_user.id}
    for photo in db.scalars(select(WorkerEnrollmentImage).where(WorkerEnrollmentImage.worker_id.in_(registered_ids))):
        evidence.append(dict(id=photo.id, worker_id=photo.worker_id, kind=f"identity_reference_{photo.view}",
            source="registry_reference_not_assessment_evidence", captured_at=_format_dt(photo.created_at),
            _path=photo.file_path, status="reference"))
    groups = {}
    worker_map = {row.id: row for row, _ in workers}
    for event in events:
        if event.event_type == "high_risk_posture":
            worker = worker_map.get(event.session_worker_id)
            key = worker.worker_id if worker and worker.identity_status == "confirmed" and worker.worker_id else event.session_worker_id
            groups.setdefault(key, []).append(event)
    manifest = dict(format_version=1, app_version="0.2.1", report_id=report_id, generated_at=_format_dt(now),
        operator_full_name=current_user.full_name,
        generated_by=current_user.email, session=dict(id=session.id, code=session.session_code,
            status=session.status, notes=session.notes, created_by=session.created_by,
            started_at=_format_dt(session.started_at), stopped_at=_format_dt(session.stopped_at),
            completed_at=_format_dt(session.completed_at)), cameras=camera_data, workers=worker_data,
        events=event_data, assessments=assessment_data, photos=evidence,
        high_risk_duration_ms=sum(merged_duration_ms(group) for group in groups.values()))
    for row in worker_data:
        related = [event for event in events if event.session_worker_id == row["id"]]
        row["observed_duration_ms"] = merged_duration_ms([e for e in related if e.event_type == "worker_observed"])
        row["high_risk_duration_ms"] = merged_duration_ms([e for e in related if e.event_type == "high_risk_posture"])
        row["high_risk_event_count"] = sum(e.event_type == "high_risk_posture" for e in related)
        for kind in ("rula", "reba"):
            stats = [(e.metadata_json or {}).get("score_stats", {}).get(kind, {}) for e in related if e.event_type == "worker_observed"]
            count = sum(int(s.get("count") or 0) for s in stats)
            row[kind] = dict(provisional_average=round(sum(int(s.get("sum") or 0) for s in stats) / count, 2) if count else None,
                             provisional_peak=max((int(s.get("peak") or 0) for s in stats), default=0) or None, samples=count)
    try:
        with ZipFile(archive_path.with_suffix(".tmp"), "w", compression=ZIP_DEFLATED) as archive:
            for photo in evidence:
                local_path = photo.pop("_path")
                if photo["status"] not in {"ready", "legacy", "reference"}:
                    photo["omission"] = "Source photo was not ready at export"
                    continue
                try:
                    content = media_path(local_path).read_bytes()
                    with PillowImage.open(BytesIO(content)) as image:
                        image.verify()
                    digest = hashlib.sha256(content).hexdigest()
                    if photo.get("expected_sha256") and digest != photo["expected_sha256"]:
                        raise ValueError("Photo checksum does not match captured source")
                    photo["sha256"] = digest
                    photo["archive_file"] = f"photos/{photo['id']}{Path(local_path).suffix.lower()}"
                    archive.writestr(photo["archive_file"], content)
                except (OSError, ValueError, SyntaxError, PillowImage.DecompressionBombError):
                    photo["omission"] = "Photo missing, invalid, outside media storage, or checksum mismatch"
            _write_pdf(output_path.with_suffix(".tmp"), manifest, detections, archive)
            output_path.with_suffix(".tmp").replace(output_path)
            archive.write(output_path, "ergonomic_report.pdf")
            manifest["pdf_sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
            # Stream raw samples into the archive instead of loading an entire long session in RAM.
            columns = ["id", "camera_node_id", "session_worker_id", "frame_id", "timestamp_ms", "observed_at",
                       "edge_worker_id", "tracking_id", "confidence", "reid_confidence", "bbox", "keypoints", "angles", "run_id", "clock_source", "pose_source", "missing_components"]
            with archive.open("detections.csv", "w") as target:
                target.write(_csv([], columns).encode("utf-8-sig"))
                query = select(Detection).where(Detection.session_id == session.id).order_by(Detection.timestamp_ms)
                for detection in db.scalars(query).yield_per(200):
                    record = {column: getattr(detection, column, None) for column in columns}
                    header = (detection.raw_payload or {}).get("event", {})
                    metadata = (detection.raw_payload or {}).get("detection", {}).get("metadata", {})
                    record.update(run_id=header.get("run_id"), clock_source=header.get("clock_source", "device_clock"))
                    record.update(pose_source=metadata.get("source"), missing_components=metadata.get("assessment_quality", {}).get("missing_components"))
                    line = _csv([record], columns, header=False)
                    target.write(line.encode("utf-8"))
            for name, rows in [("workers", worker_data), ("events", event_data), ("assessments", assessment_data)]:
                archive.writestr(f"{name}.csv", _csv(rows, list(rows[0]) if rows else ["id"]).encode("utf-8-sig"))
            archive.writestr("manifest.json", _json(manifest).encode("utf-8"))
        archive_path.with_suffix(".tmp").replace(archive_path)
        report = Report(id=report_id, owner_user_id=current_user.id, session_id=session.id,
            report_type="session_pdf", status="ready", file_path=str(output_path), generated_by=current_user.email,
            generated_at=now, metadata_json=dict(session_code=session.session_code, event_count=len(events),
                worker_count=len(workers), reviewed_assessment_count=sum(a.assessment_status == "reviewed" for a in assessments),
                photo_count=sum("archive_file" in photo for photo in evidence),
                omitted_photo_count=sum("omission" in photo for photo in evidence), archive_path=str(archive_path)))
        db.add(report)
        db.commit()
    except Exception:
        db.rollback()
        # Only this new report's files are removed; existing reports and source evidence stay untouched.
        for path in report_dir.iterdir():
            path.unlink()
        report_dir.rmdir()
        raise
    db.refresh(report)
    return report


def _write_pdf(output_path, data, detections, archive):
    font_dir = Path(reportlab.__file__).parent / "fonts"
    if "ErgoBody" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ErgoBody", str(font_dir / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("ErgoBold", str(font_dir / "VeraBd.ttf")))
    styles = getSampleStyleSheet()
    for name in ("BodyText", "Normal", "Title", "Heading1", "Heading2", "Heading3"):
        styles[name].fontName = "ErgoBody" if name in {"BodyText", "Normal"} else "ErgoBold"
    styles["BodyText"].fontSize = 8
    styles["BodyText"].leading = 11
    story = []

    def text(value, style="BodyText"):
        return Paragraph(escape(str(value if value is not None else "Not measured / unavailable")).replace("\n", "<br/>"), styles[style])

    def table(rows, widths=(40 * mm, 142 * mm), header=False):
        result = LongTable([[text(cell) for cell in row] for row in rows], colWidths=widths,
                           repeatRows=1 if header else 0, hAlign="LEFT", splitInRow=1)
        result.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#d8dedf")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("BACKGROUND", (0, 0), (-1, 0) if header else (0, -1), colors.HexColor("#edf3f2"))]))
        story.append(result)
        story.append(Spacer(1, 6))

    def fields(values, prefix=""):
        for key, value in values.items():
            label = f"{prefix}{key}".replace("_", " ")
            if isinstance(value, dict):
                fields(value, label + " / ")
            else:
                displayed = _json(value) if isinstance(value, list) else "Not measured / unavailable" if value is None else value
                story.append(text(f"{label}: {displayed}"))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(14 * mm, 8 * mm, f"ERGoSIGHT | {data['report_id']}")
        canvas.drawRightString(196 * mm, 8 * mm, f"{doc.page}")
        canvas.restoreState()

    assets = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "assets"
    logo = assets / "ergosight-logo.png"
    if logo.is_file():
        image = Image(str(logo), width=48 * mm, height=25 * mm, kind="proportional")
        image.hAlign = "LEFT"
        story.append(image)
    story.append(text("ERGoSIGHT", "Title"))
    story.append(text("Ergonomic Session Report", "Heading1"))
    story.append(text(f"Generated {data['generated_at']} by {data.get('operator_full_name') or data['generated_by']} | Version {data['app_version']}"))
    story.append(text("Assessment limitations", "Heading2"))
    story.append(text("Single-camera 2D estimates are provisional, not a validated ergonomic diagnosis. Missing angles are not zero. "
        "Wrist twist, force, coupling and activity require operator verification. Track IDs are not confirmed human identities. "
        "Legacy/reference photos are not verified posture evidence. All times below are UTC. Documentation contains personal data; share only with authorized recipients."))
    story.append(text("Session Summary", "Heading2"))
    table(list(data["session"].items()) + [["High risk exposure (overlap merged)", f"{data['high_risk_duration_ms'] / 1000:.1f} seconds"]])
    story.append(text("Cameras", "Heading2"))
    for camera in data["cameras"]:
        table(list(camera.items()))
    story.append(text("Workers and Identity Scope", "Heading2"))
    if not data["workers"]:
        story.append(text("No workers recorded."))
    for worker in data["workers"]:
        rows = []
        for key, value in worker.items():
            if key in {"rula", "reba"}:
                value = f"Provisional average: {value['provisional_average'] if value['samples'] else '-'}; peak: {value['provisional_peak'] or '-'}; samples: {value['samples']}"
            rows.append([key.replace('_', ' '), value])
        table(rows)
    story.append(text("Assessments - Provisional and Reviewed", "Heading2"))
    if not data["assessments"]:
        story.append(text("No assessments recorded."))
    for assessment in data["assessments"]:
        story.append(text(f"{assessment['type'].upper()} | {assessment['status']} | {assessment['id']}", "Heading3"))
        fields(assessment)
        story.append(Spacer(1, 8))
    story.append(text("Observation and Risk Timeline", "Heading2"))
    if not data["events"]:
        story.append(text("No events recorded."))
    for event in data["events"]:
        story.append(text(event["event_type"].replace("_", " ").title(), "Heading3"))
        table(list(event.items()))
        source = detections.get(event["source_detection_id"])
        if source:
            story.append(text("Source pose measurements (degrees)", "Heading3"))
            table(_angle_rows(source))
            header = (source.raw_payload or {}).get("event", {})
            fields(dict(detection_id=source.id, frame_id=source.frame_id, captured_at=_format_dt(source.observed_at),
                        confidence=source.confidence, clock_source=header.get("clock_source", "device_clock"),
                        run_id=header.get("run_id")))
            source_metadata = (source.raw_payload or {}).get("detection", {}).get("metadata", {})
            quality = source_metadata.get("assessment_quality", {})
            fields(dict(pose_source=source_metadata.get("source"), quality_status=quality.get("status"), missing_components=quality.get("missing_components")))
        else:
            story.append(text("Source detection unavailable; no pose measurements inferred."))
        story.append(text("Photos: " + (", ".join(photo["id"] for photo in data["photos"] if photo.get("event_id") == event["id"]) or "None")))
    story.append(text("Documentation Photos", "Heading2"))
    if not data["photos"]:
        story.append(text("No documentation photos recorded."))
    for photo in data["photos"]:
        story.append(text(f"{photo['kind']} | {photo['id']}", "Heading3"))
        if "archive_file" in photo:
            content = archive.read(photo["archive_file"])
            image = Image(BytesIO(content))
            scale = min(182 * mm / image.imageWidth, 96 * mm / image.imageHeight)
            image.drawWidth, image.drawHeight = image.imageWidth * scale, image.imageHeight * scale
            image.hAlign = "LEFT"
            story.append(image)
        fields(photo)
        source = detections.get(photo.get("detection_id"))
        if source:
            table(_angle_rows(source))
        story.append(Spacer(1, 10))
    SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm, title=f"{data['session']['code']} Ergonomic Report").build(
            story, onFirstPage=footer, onLaterPages=footer)
