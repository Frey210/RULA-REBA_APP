from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.security import create_access_token
from app.models.camera_node import CameraNode
from app.models.detection import Detection
from app.models.ergonomic_event import ErgonomicEvent
from app.models.session import Session
from app.models.session_worker import SessionWorker
from app.models.snapshot import Snapshot
from app.models.user import User
from app.schemas.edge import EdgeDetectionEvent
from app.services.detection_ingest import persist_detection_event
from app.services.edge_devices import issue_device_token, refresh_camera
from app.services.event_engine import process_presence_timeouts, resolve_active_events_for_session
from app.services.snapshot_capture import capture_pending_evidence
from app.services.exposure_intervals import merged_duration_ms


@pytest.fixture
def recording(db_session, edge_stub, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_root", tmp_path)
    user = User(email="owner@test.local", username="owner", password_hash="unused")
    other = User(email="other@test.local", username="other", password_hash="unused")
    db_session.add_all([user, other])
    db_session.flush()
    camera = CameraNode(cam_id="CAM_01", owner_user_id=user.id, metadata_json={
        "edge_base_url": "http://edge.test", "device_id": "00000000-0000-4000-8000-000000000001"})
    db_session.add(camera)
    db_session.flush()
    secret = issue_device_token(camera)
    run_id = str(uuid4())
    session = Session(owner_user_id=user.id, session_code="SESSION_AUDIT", status="running",
                      metadata_json={"camera_node_ids": [camera.cam_id], "edge_runs": {camera.cam_id: run_id}})
    db_session.add(session)
    db_session.commit()
    return user, other, camera, session, secret


def sample(recording, frame=1, offset=0, angles=None, empty=False):
    user, other, camera, session, secret = recording
    angles = angles if angles is not None else dict(neck=35, trunk=75, ua_l=100, ua_r=100,
             la_l=120, la_r=120, leg_l=70, leg_r=70, wrist_l=30, wrist_r=30)
    return EdgeDetectionEvent.model_validate({"event_type": "detection", "cam_id": camera.cam_id,
        "session_id": session.session_code, "run_id": session.metadata_json["edge_runs"][camera.cam_id],
        "timestamp": int(datetime.now(UTC).timestamp() * 1000) + offset, "frame_id": frame,
        "detections": [] if empty else [{"worker_id": "REID_0001", "tracking_id": 1,
            "confidence": .9, "bbox": [10, 10, 150, 300], "keypoints": {"points": []},
            "metadata": {"angles": angles}}]})


def test_authenticated_detection_is_persisted_and_fanned_out(client, recording, db_session):
    user, other, camera, session, secret = recording
    token = create_access_token(user.id)
    with client.websocket_connect(f"/ws/v1/sessions/{session.session_code}/live", headers={"Authorization": f"Bearer {token}"}) as live:
        with client.websocket_connect("/ws/v1/edge/CAM_01", headers={"Authorization": f"Bearer {secret}"}) as edge:
            edge.send_json(sample(recording).model_dump())
            assert edge.receive_json()["event_type"] == "ack"
            assert live.receive_json()["cam_id"] == camera.cam_id
    assert db_session.scalar(select(func.count()).select_from(Detection)) == 1


def test_live_and_edge_require_the_right_owner_and_credential(client, recording):
    user, other, camera, session, secret = recording
    for url, headers in [
        ("/ws/v1/edge/CAM_01", {}),
        (f"/ws/v1/sessions/{session.session_code}/live", {"Authorization": f"Bearer {create_access_token(other.id)}"}),
    ]:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url, headers=headers):
                pass


def test_duplicate_frames_do_not_duplicate_samples(recording, db_session):
    event = sample(recording)
    assert persist_detection_event(db_session, event) == 1
    assert persist_detection_event(db_session, event) == -1
    assert db_session.scalar(select(func.count()).select_from(Detection)) == 1
    assert persist_detection_event(db_session, sample(recording, frame=0, offset=-1000)) == -1


def test_finished_sessions_wrong_runs_and_foreign_cameras_are_rejected(recording, db_session):
    event = sample(recording)
    event.run_id = "wrong-run"
    with pytest.raises(ValueError):
        persist_detection_event(db_session, event)
    event = sample(recording)
    recording[3].status = "completed"
    db_session.commit()
    with pytest.raises(ValueError):
        persist_detection_event(db_session, event)
    recording[3].status = "running"
    recording[2].owner_user_id = recording[1].id
    db_session.commit()
    with pytest.raises(ValueError):
        persist_detection_event(db_session, event)


def test_camera_local_ids_are_distinct(recording, db_session):
    persist_detection_event(db_session, sample(recording))
    camera = CameraNode(cam_id="CAM_02", owner_user_id=recording[0].id)
    db_session.add(camera)
    db_session.flush()
    session = recording[3]
    session.metadata_json = {"camera_node_ids": ["CAM_01", "CAM_02"],
        "edge_runs": {**session.metadata_json["edge_runs"], "CAM_02": str(uuid4())}}
    db_session.commit()
    event = sample(recording)
    event.cam_id = "CAM_02"
    event.run_id = session.metadata_json["edge_runs"]["CAM_02"]
    persist_detection_event(db_session, event)
    assert db_session.scalar(select(func.count()).select_from(SessionWorker)) == 2


def test_missing_person_does_not_add_unobserved_exposure(recording, db_session):
    persist_detection_event(db_session, sample(recording))
    process_presence_timeouts(db_session, recording[3], datetime.now(UTC) + timedelta(seconds=5))
    resolve_active_events_for_session(db_session, recording[3], datetime.now(UTC) + timedelta(minutes=1))
    db_session.commit()
    risk = db_session.scalar(select(ErgonomicEvent).where(ErgonomicEvent.event_type == "high_risk_posture"))
    assert risk.status == "resolved" and risk.duration_ms == 0
    assert not db_session.scalar(select(ErgonomicEvent.id).where(ErgonomicEvent.event_type.in_(["worker_entered", "worker_left"])))


def test_better_pose_replaces_initial_poor_source(recording, db_session):
    persist_detection_event(db_session, sample(recording, angles={"wrist_l": None, "wrist_r": None}))
    observation = db_session.scalar(select(ErgonomicEvent).where(ErgonomicEvent.event_type == "worker_observed"))
    before = observation.source_detection_id
    persist_detection_event(db_session, sample(recording, frame=2, offset=1000))
    db_session.refresh(observation)
    assert observation.source_detection_id != before


def test_incomplete_pose_cannot_be_finalized(client, recording, db_session):
    persist_detection_event(db_session, sample(recording, angles={"neck": None, "wrist_l": 0}))
    observation = db_session.scalar(select(ErgonomicEvent).where(ErgonomicEvent.event_type == "worker_observed"))
    response = client.put(f"/api/v1/sessions/{recording[3].id}/events/{observation.id}/reviews/reba",
        headers={"Authorization": f"Bearer {create_access_token(recording[0].id)}"}, json={})
    assert response.status_code == 409


def test_verified_source_evidence_review_and_private_report(client, recording, db_session):
    persist_detection_event(db_session, sample(recording))
    capture_pending_evidence()
    observation = db_session.scalar(select(ErgonomicEvent).where(ErgonomicEvent.event_type == "worker_observed"))
    headers = {"Authorization": f"Bearer {create_access_token(recording[0].id)}"}
    path = f"/api/v1/sessions/{recording[3].id}/events/{observation.id}"
    detail = client.get(path, headers=headers).json()
    assert detail["snapshots"][0]["metadata"]["frame_id"] == 1
    content = client.get(detail["snapshots"][0]["content_url"], headers=headers)
    assert content.headers["content-type"] == "image/jpeg"
    assert client.put(path + "/reviews/reba", headers=headers, json={"load_score": 2}).status_code == 200
    before = Path(db_session.scalar(select(Snapshot.file_path).where(Snapshot.ergonomic_event_id == observation.id))).read_bytes()
    assert client.post(path + "/snapshots", headers=headers).status_code == 503
    assert before == Path(db_session.scalar(select(Snapshot.file_path).where(Snapshot.ergonomic_event_id == observation.id))).read_bytes()
    recording[3].status = "review_pending"
    db_session.commit()
    report = client.post(f"/api/v1/reports/sessions/{recording[3].id}", headers=headers).json()
    assert client.get(report["download_url"], headers=headers).content.startswith(b"%PDF")
    assert client.get(report["download_url"], headers={"Authorization": f"Bearer {create_access_token(recording[1].id)}"}).status_code == 404


def test_expired_or_mismatched_frame_is_never_replaced_by_latest(client, recording, db_session, monkeypatch):
    persist_detection_event(db_session, sample(recording))
    monkeypatch.setattr("app.services.snapshot_capture.edge_request", lambda *a, **k:
        httpx.Response(200, content=b"wrong image", headers={"x-frame-id": "999"}))
    capture_pending_evidence()
    assert not db_session.scalar(select(Snapshot.id).where(Snapshot.file_path != ""))


def test_offline_device_and_failed_start_are_honest(client, recording, db_session, monkeypatch):
    def offline(*a, **k):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("app.services.edge_devices.edge_http.request", offline)
    camera, session = recording[2:4]
    camera.status = "online"
    refresh_camera(camera)
    assert camera.status == "offline"
    session.status = "created"
    db_session.commit()
    response = client.post(f"/api/v1/sessions/{session.id}/start",
        headers={"Authorization": f"Bearer {create_access_token(recording[0].id)}"})
    assert response.status_code == 503
    db_session.refresh(session)
    assert session.status == "failed"


def test_browser_authentication_does_not_put_tokens_in_the_url(client, recording):
    user, _, _, session, secret = recording
    with client.websocket_connect(f"/ws/v1/sessions/{session.session_code}/live") as live:
        live.send_json({"token": create_access_token(user.id)})
        with client.websocket_connect("/ws/v1/edge/CAM_01", headers={"Authorization": f"Bearer {secret}"}) as edge:
            edge.send_json(sample(recording).model_dump())
            assert edge.receive_json()["event_type"] == "ack"
        assert live.receive_json()["event_type"] == "session_detection"


def test_missing_angles_require_explicit_manual_values(client, recording, db_session):
    event = sample(recording)
    event.detections[0].metadata["angles"]["wrist_l"] = None
    persist_detection_event(db_session, event)
    capture_pending_evidence()
    observation = db_session.scalar(select(ErgonomicEvent).where(ErgonomicEvent.event_type == "worker_observed"))
    path = f"/api/v1/sessions/{recording[3].id}/events/{observation.id}/reviews/reba"
    headers = {"Authorization": f"Bearer {create_access_token(recording[0].id)}"}
    assert client.put(path, headers=headers, json={}).status_code == 409
    reviewed = client.put(path, headers=headers, json={"angle_overrides": {"wrist_l": 20}})
    assert reviewed.status_code == 200
    assert reviewed.json()["angle_overrides"] == {"wrist_l": 20}
    assert client.put(path, headers=headers, json={"angle_overrides": {"wrist_l": 999}}).status_code == 422


def test_overlapping_camera_exposure_is_counted_once():
    from types import SimpleNamespace
    start = datetime.now(UTC)
    first = SimpleNamespace(started_at=start, ended_at=start + timedelta(seconds=10), duration_ms=10000)
    second = SimpleNamespace(started_at=start + timedelta(seconds=5), ended_at=start + timedelta(seconds=15), duration_ms=10000)
    assert merged_duration_ms([first, second]) == 15000


def test_operator_disappearance_stops_the_session(recording, db_session, edge_stub):
    from app.services.device_monitor import monitor_devices
    session = recording[3]
    session.metadata_json = {**session.metadata_json,
        "operator_last_seen": (datetime.now(UTC) - timedelta(seconds=30)).isoformat(),
        "lease_confirmed_at": datetime.now(UTC).isoformat()}
    db_session.commit()
    monitor_devices()
    db_session.refresh(session)
    assert session.status == "review_pending"
