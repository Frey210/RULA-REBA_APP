import re
import sys
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from app.services.report_content import flatten, label, references


def source_photo(event, photos):
    return next((photo for photo in photos if event.get('source_detection_id') and photo.get('event_id') == event['id']
                 and photo.get('detection_id') == event['source_detection_id'] and 'archive_file' in photo), None)


def write_pdf(output_path, data, detections, archive):
    fonts = Path(reportlab.__file__).parent / "fonts"
    for name, filename in (("ErgoBody", "Vera.ttf"), ("ErgoBold", "VeraBd.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    styles = {
        "body": ParagraphStyle("ReportBody", fontName="ErgoBody", fontSize=9, leading=14, spaceAfter=7, splitLongWords=True),
        "cell": ParagraphStyle("ReportCell", fontName="ErgoBody", fontSize=8, leading=12, spaceAfter=0, splitLongWords=True),
        "header": ParagraphStyle("ReportHeader", fontName="ErgoBold", fontSize=8, leading=12, textColor=colors.white),
        "title": ParagraphStyle("ReportTitle", fontName="ErgoBold", fontSize=22, leading=29, spaceAfter=14),
        "section": ParagraphStyle("ReportSection", fontName="ErgoBold", fontSize=13, leading=19, spaceBefore=12, spaceAfter=10, keepWithNext=True),
        "small": ParagraphStyle("ReportSmall", fontName="ErgoBody", fontSize=8, leading=12, textColor=colors.HexColor("#46555c"), spaceAfter=7),
    }
    refs = references(data)
    workers = {row["id"]: row for row in data["workers"]}
    registry_names = {row['worker_id']: row['name'] for row in data['workers'] if row['worker_id']}
    story = []

    def text(value, style="body"):
        value = "Not measured / unavailable" if value is None else str(value)
        value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
        return Paragraph(escape(value).replace("\n", "<br/>"), styles[style])

    def table(rows, widths=(48, 134), header=False):
        rendered = [[text(value, "header" if header and index == 0 else "cell") for value in row] for index, row in enumerate(rows)]
        item = LongTable(rendered, colWidths=[value * mm for value in widths], hAlign="LEFT",
                         repeatRows=1 if header else 0, splitInRow=1)
        commands = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), .35, colors.HexColor("#dce4e8"))]
        if header:
            commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#006d91")))
        else:
            commands.append(("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f5f7")))
        item.setStyle(TableStyle(commands))
        story.extend([item, Spacer(1, 9)])

    def heading(value):
        story.append(text(value, "section"))

    def new_page(title):
        story.append(PageBreak())
        story.append(text(title, "title"))

    def worker_name(worker_id):
        row = workers.get(worker_id, {})
        return f"{row.get('name', 'Unassigned')} ({refs.get(worker_id, '-')})"

    def photo_image(photo, height=92):
        if "archive_file" not in photo:
            story.append(text(photo.get("omission", "Photo unavailable"), "small"))
            return
        image = Image(BytesIO(archive.read(photo["archive_file"])))
        scale = min(182 * mm / image.imageWidth, height * mm / image.imageHeight)
        image.drawWidth, image.drawHeight = image.imageWidth * scale, image.imageHeight * scale
        image.hAlign = "LEFT"
        story.extend([image, Spacer(1, 8)])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dce4e8"))
        canvas.line(14 * mm, 13 * mm, 196 * mm, 13 * mm)
        canvas.setFont("ErgoBody", 7)
        canvas.drawString(14 * mm, 8 * mm, f"ERGoSIGHT  /  {data['session']['code']}")
        canvas.drawRightString(196 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    assets = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "assets"
    if (assets / "ergosight-logo.png").is_file():
        image = Image(str(assets / "ergosight-logo.png"), width=45 * mm, height=24 * mm, kind="proportional")
        image.hAlign = "LEFT"
        story.extend([image, Spacer(1, 12)])
    story.append(text("Ergonomic Session Report", "title"))
    story.append(text(data["session"]["code"]))
    story.append(text(f"Generated {data['generated_at']} by {data.get('operator_full_name') or data['generated_by']}", "small"))
    table([["Worker tracks", "Events", "Reviewed", "Photos"], [len(data["workers"]), len(data["events"]),
        sum(row["status"] == "reviewed" for row in data["assessments"]),
        sum("archive_file" in row for row in data["photos"])]], widths=(45.5, 45.5, 45.5, 45.5), header=True)
    heading("Session summary")
    table([[label(key), data["session"].get(key)] for key in ("status", "created_by", "started_at", "stopped_at", "completed_at")] +
          [["High-risk exposure", f"{data['high_risk_duration_ms'] / 1000:.1f} seconds (overlap merged)"]])
    if data["session"].get("notes"):
        heading("Session notes")
        story.append(text(data["session"]["notes"]))
    heading("Assessment limitations")
    story.append(text("Single-camera 2D scores are provisional estimates, not a validated ergonomic diagnosis. Missing angles are not zero. "
        "Force, activity, coupling and wrist twist require operator review. Track IDs do not prove a unique human identity. "
        "All times are UTC. This report contains personal data.", "small"))

    new_page("Workers and cameras")
    heading("Cameras")
    table([["Camera", "Hostname", "Device type"], *[[c["cam_id"], c["hostname"], c["device_type"]] for c in data["cameras"]]], (35, 82, 65), True)
    heading("Worker exposure by track")
    if not data["workers"]:
        story.append(text("No workers recorded."))
    for worker in data["workers"]:
        heading(worker_name(worker["id"]))
        table([["Track / camera", f"{worker['edge_worker_id']} / {refs.get(worker['camera_node_id'], '-')}"],
            ["Identity", label(worker["identity_status"])], ["Employee / department", f"{worker['employee_number'] or '-'} / {worker['department'] or '-'}"],
            ["Position", worker["position"]], ["Observed / high risk", f"{worker['observed_duration_ms'] / 1000:.1f} s / {worker['high_risk_duration_ms'] / 1000:.1f} s"],
            *[[f"{kind.upper()} provisional", f"Average {worker[kind]['provisional_average'] if worker[kind]['samples'] else '-'}; peak {worker[kind]['provisional_peak'] or '-'}; {worker[kind]['samples']} samples"] for kind in ("rula", "reba")]])

    for event in data["events"]:
        new_page(f"{refs[event['id']]}  {label(event['event_type'])}")
        story.append(text(f"{worker_name(event['session_worker_id'])}  /  {refs.get(event['camera_node_id'], '-')}"))
        table([["Started / ended", f"{event['started_at']} / {event['ended_at']}"],
            ["Duration / severity", f"{(event['duration_ms'] or 0) / 1000:.1f} s / {label(event['severity'])}"],
            ["Provisional risk", f"{(event['score_type'] or '-').upper()} {event['score'] if event['score'] is not None else '-'} / {event['risk_level'] or '-'}"],
            ["Review references", ", ".join(refs[a["id"]] for a in data["assessments"] if a["event_id"] == event["id"]) or "No review"]])
        photo = source_photo(event, data['photos'])
        if photo:
            photo_image(photo, 65)
            story.append(text(f"Photo {refs[photo['id']]} - {photo['captured_at']}", "small"))
        else:
            story.append(text("Source frame photo unavailable. Other event photos, if any, are in the photo appendix.", "small"))
        source = detections.get(event["source_detection_id"])
        heading("Source pose measurements (degrees)")
        if source:
            angles = source.angles or {}
            table([["Component", "Left / value", "Right"], ["Neck", angles.get("neck"), "-"], ["Trunk", angles.get("trunk"), "-"],
                *[[title, angles.get(left), angles.get(right)] for title, left, right in
                  (("Upper arm", "ua_l", "ua_r"), ("Lower arm", "la_l", "la_r"), ("Knee", "leg_l", "leg_r"), ("Wrist", "wrist_l", "wrist_r"))]], (64, 59, 59), True)
        else:
            story.append(text("Source measurements unavailable; no angle inferred."))

    for assessment in data["assessments"]:
        new_page(f"{refs[assessment['id']]}  {assessment['type'].upper()} assessment")
        story.append(text(worker_name(assessment["session_worker_id"])))
        table([["Status / event", f"{label(assessment['status'])} / {refs.get(assessment['event_id'], '-')}"],
            ["Reviewed score / risk" if assessment["status"] == "reviewed" else "Provisional score / risk", f"{assessment['score']} / {assessment['risk_level']}"],
            ["Original provisional score", assessment["provisional_score"]], ["Group A / B", f"{assessment['score_a'] if assessment['score_a'] is not None else '-'} / {assessment['score_b'] if assessment['score_b'] is not None else '-'}"],
            ["Calculated", assessment["calculated_at"]]])
        heading("Scoring inputs and component breakdown")
        rows = list(flatten(assessment["breakdown"] or {}))
        if rows:
            table(rows)
        else:
            story.append(text("No component breakdown recorded."))
        heading("Review notes")
        story.append(text(assessment["review_notes"] or "No review notes."))

    for photo in data["photos"]:
        new_page(f"{refs[photo['id']]}  Documentation photo")
        story.append(text(worker_name(photo['session_worker_id']) if photo.get('session_worker_id') else
                          registry_names.get(photo.get('worker_id'), 'Registry identity reference')))
        photo_image(photo)
        table([["Photo type", label(photo["kind"])], ["Captured", photo["captured_at"]],
            ["Camera / event", f"{refs.get(photo.get('camera_node_id'), '-')} / {refs.get(photo.get('event_id'), '-')}"],
            ["Evidence source", label(photo["source"])], ["Frame / status", f"{photo.get('frame_id', '-')} / {label(photo['status'])}"],
            ["Source run", photo.get('run_id')], ["SHA-256", photo.get('sha256')]])
        if photo.get("omission"):
            story.append(text(photo["omission"]))
        story.append(text("Registry references and legacy photos are not verified posture evidence.", "small"))

    new_page("Technical references")
    story.append(text("Stable references for audit. Full technical identifiers, sample data and original photos are in Excel and the documentation ZIP.", "small"))
    table([["Report ID", data["report_id"]], ["Session ID", data["session"]["id"]], ["Application version", data["app_version"]]])
    table([["Camera", "Device UUID"], *[[c['cam_id'], c['device_id']] for c in data['cameras']]], (40, 142), True)
    rows = [["Reference", "Record", "Record ID"]]
    for collection in ("workers", "events", "assessments", "photos"):
        rows.extend([[refs[row['id']], label(collection), row['id']] for row in data[collection]])
    table(rows, (28, 40, 114), True)
    SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=16 * mm, bottomMargin=19 * mm, title=f"{data['session']['code']} Ergonomic Report").build(
        story, onFirstPage=footer, onLaterPages=footer)
