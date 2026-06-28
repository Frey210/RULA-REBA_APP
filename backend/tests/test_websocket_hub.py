from io import BytesIO
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.assessment import Assessment
from app.models.detection import Detection
from app.models.ergonomic_event import ErgonomicEvent
from app.models.session import Session as AssessmentSession
from app.models.session_worker import SessionWorker
from app.models.snapshot import Snapshot
from app.core.config import settings


def get_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ws@example.com",
            "username": "ws-user",
            "password": "strong-password",
            "full_name": "WS User",
        },
    )
    assert response.status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ws@example.com", "password": "strong-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_edge_detection_is_fanned_out_to_session_subscriber(client: TestClient) -> None:
    token = get_token(client)
    detection_payload = {
        "schema_version": "1.0",
        "event_type": "detection",
        "cam_id": "CAM_01",
        "session_id": "SESSION_TEST_001",
        "timestamp": 1718742953123,
        "frame_id": 42,
        "detections": [
            {
                "worker_id": "WORKER_E47A",
                "tracking_id": 4,
                "confidence": 0.92,
                "reid_confidence": 0.88,
                "bbox": [120.5, 80.0, 420.0, 720.0],
                "keypoints": {
                    "format": "coco17",
                    "points": [{"id": 0, "name": "nose", "x": 231.0, "y": 96.0, "score": 0.86}],
                },
                "snapshot_path": "/tmp/snapshot.jpg",
                "metadata": {"model": "yolov8s_pose_h8"},
            }
        ],
    }

    with client.websocket_connect(f"/ws/v1/sessions/SESSION_TEST_001/live?token={token}") as live_ws:
        with client.websocket_connect("/ws/v1/edge/CAM_01") as edge_ws:
            edge_ws.send_json(detection_payload)
            assert edge_ws.receive_json()["event_type"] == "ack"

        live_event = live_ws.receive_json()
        assert live_event["event_type"] == "session_detection"
        assert live_event["session_id"] == "SESSION_TEST_001"
        assert live_event["detections"][0]["worker_id"] == "WORKER_E47A"


def test_edge_rejects_cam_id_mismatch(client: TestClient) -> None:
    with client.websocket_connect("/ws/v1/edge/CAM_02") as edge_ws:
        edge_ws.send_json(
            {
                "schema_version": "1.0",
                "event_type": "detection",
                "cam_id": "CAM_01",
                "session_id": "SESSION_TEST_001",
                "timestamp": 1718742953123,
                "frame_id": 42,
                "detections": [],
            }
        )
        response = edge_ws.receive_json()
        assert response["event_type"] == "error"
        assert response["code"] == "CAM_ID_MISMATCH"


def test_edge_detection_is_persisted_for_known_session_and_camera(
    client: TestClient,
    db_session: Session,
    monkeypatch,
    tmp_path,
) -> None:
    image_buffer = BytesIO()
    Image.new("RGB", (640, 360), color=(20, 90, 84)).save(image_buffer, format="JPEG")

    def snapshot_response(*_args, **_kwargs) -> httpx.Response:
        return httpx.Response(
            200,
            content=image_buffer.getvalue(),
            headers={"content-type": "image/jpeg"},
            request=httpx.Request("GET", "http://edge.test/snapshot/latest"),
        )

    monkeypatch.setattr(settings, "media_root", tmp_path)
    monkeypatch.setattr("app.services.snapshot_capture.httpx.get", snapshot_response)
    token = get_token(client)
    pairing = client.post("/api/v1/device-pairings", headers={"Authorization": f"Bearer {token}"})
    assert pairing.status_code == 201
    complete = client.post(
        "/api/v1/device-pairings/complete",
        json={
            "pairing_code": pairing.json()["pairing_code"],
            "cam_id": "CAM_01",
            "hostname": "ergoquipt-rr",
            "device_type": "raspberry_pi_5_hailo8",
            "metadata": {"hailort": "4.23.0", "edge_base_url": "http://edge.test"},
        },
    )
    assert complete.status_code == 200

    session = client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"camera_node_ids": ["CAM_01"], "notes": "Persist websocket"},
    )
    assert session.status_code == 201
    session_code = session.json()["session_code"]

    with client.websocket_connect("/ws/v1/edge/CAM_01") as edge_ws:
        edge_ws.send_json(
            {
                "schema_version": "1.0",
                "event_type": "detection",
                "cam_id": "CAM_01",
                "session_id": session_code,
                "timestamp": 1718742953123,
                "frame_id": 100,
                "detections": [
                    {
                        "worker_id": "WORKER_E47A",
                        "tracking_id": 4,
                        "confidence": 0.92,
                        "reid_confidence": 0.88,
                        "bbox": [120.5, 80.0, 420.0, 720.0],
                        "keypoints": {
                            "format": "coco17",
                            "points": [
                                {"id": 0, "name": "nose", "x": 231.0, "y": 96.0, "score": 0.86}
                            ],
                        },
                        "metadata": {
                            "model": "yolov8s_pose_h8",
                            "identity_status": "new",
                            "reba": {"score": 3, "risk": "Low"},
                            "rula": {"score": 6, "risk": "High"},
                        },
                    }
                ],
            }
        )
        assert edge_ws.receive_json()["event_type"] == "ack"
        edge_ws.send_json(
            {
                "schema_version": "1.0",
                "event_type": "detection",
                "cam_id": "CAM_01",
                "session_id": session_code,
                "timestamp": 1718742964123,
                "frame_id": 101,
                "detections": [
                    {
                        "worker_id": "WORKER_E47A",
                        "tracking_id": 4,
                        "confidence": 0.9,
                        "reid_confidence": 0.91,
                        "bbox": [124.0, 82.0, 418.0, 718.0],
                        "keypoints": {"format": "coco17", "points": []},
                        "metadata": {
                            "identity_status": "tracked",
                            "reba": {"score": 3, "risk": "Low"},
                            "rula": {"score": 6, "risk": "High"},
                        },
                    }
                ],
            }
        )
        assert edge_ws.receive_json()["event_type"] == "ack"
        edge_ws.send_json(
            {
                "schema_version": "1.0",
                "event_type": "detection",
                "cam_id": "CAM_01",
                "session_id": session_code,
                "timestamp": 1718742965123,
                "frame_id": 102,
                "detections": [
                    {
                        "worker_id": "WORKER_E47A",
                        "tracking_id": 9,
                        "confidence": 0.9,
                        "reid_confidence": 0.91,
                        "bbox": [124.0, 82.0, 418.0, 718.0],
                        "keypoints": {"format": "coco17", "points": []},
                        "metadata": {
                            "identity_status": "reacquired",
                            "reba": {"score": 3, "risk": "Low"},
                        },
                    }
                ],
            }
        )
        assert edge_ws.receive_json()["event_type"] == "ack"
        edge_ws.send_json(
            {
                "schema_version": "1.0",
                "event_type": "detection",
                "cam_id": "CAM_01",
                "session_id": session_code,
                "timestamp": 1718742968123,
                "frame_id": 103,
                "detections": [],
            }
        )
        assert edge_ws.receive_json()["event_type"] == "ack"

    detections = list(db_session.scalars(select(Detection)))
    assert len(detections) == 3
    assert detections[0].edge_worker_id == "WORKER_E47A"
    assert detections[0].frame_id == 100
    session_workers = list(db_session.scalars(select(SessionWorker)))
    assert len(session_workers) == 1
    assert session_workers[0].edge_worker_id == "WORKER_E47A"
    assert session_workers[0].tracking_id == 9
    assert session_workers[0].identity_status == "reacquired"
    assert all(detection.session_worker_id == session_workers[0].id for detection in detections)
    events = list(db_session.scalars(select(ErgonomicEvent).order_by(ErgonomicEvent.created_at)))
    event_types = [event.event_type for event in events]
    assert event_types.count("worker_observed") == 1
    assert event_types.count("worker_entered") == 1
    assert event_types.count("worker_left") == 1
    assert event_types.count("high_risk_posture") == 1
    assert event_types.count("sustained_high_risk") == 1
    high_risk_row = next(event for event in events if event.event_type == "high_risk_posture")
    assert high_risk_row.status == "resolved"
    assert high_risk_row.score_type == "rula"
    assert high_risk_row.score == 6
    assert high_risk_row.duration_ms == 12000

    listed = client.get(
        f"/api/v1/sessions/{session.json()['id']}/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert any(event["event_type"] == "high_risk_posture" for event in listed.json())
    summary = client.get(
        f"/api/v1/sessions/{session.json()['id']}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary.status_code == 200
    assert summary.json()["worker_count"] == 1
    assert summary.json()["high_risk_event_count"] == 1
    assert summary.json()["sustained_event_count"] == 1
    assert summary.json()["high_risk_duration_ms"] == 12000
    assert summary.json()["workers"][0]["detection_count"] == 3
    assert summary.json()["workers"][0]["rula"] == {
        "average": 6.0,
        "peak": 6,
        "samples": 2,
    }
    high_risk_event = next(
        event for event in listed.json() if event["event_type"] == "high_risk_posture"
    )
    detail = client.get(
        f"/api/v1/sessions/{session.json()['id']}/events/{high_risk_event['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    assert detail.json()["provisional_scores"]["rula"]["score"] == 6
    assert len(detail.json()["snapshots"]) == 1
    snapshot_content = client.get(
        detail.json()["snapshots"][0]["content_url"],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert snapshot_content.status_code == 200
    assert snapshot_content.headers["content-type"] == "image/jpeg"

    reviewed = client.put(
        f"/api/v1/sessions/{session.json()['id']}/events/{high_risk_event['id']}/reviews/reba",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "load_score": 2,
            "coupling_score": 1,
            "activity_score": 1,
            "notes": "Load confirmed from the event evidence.",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["assessment_status"] == "reviewed"
    assert reviewed.json()["manual_inputs"] == {
        "load_score": 2,
        "coupling_score": 1,
        "activity_score": 1,
    }
    assert reviewed.json()["provisional_score"] == 3
    assert reviewed.json()["score"] >= reviewed.json()["provisional_score"]
    reviewed_events = client.get(
        f"/api/v1/sessions/{session.json()['id']}/events",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    reviewed_high_risk = next(
        event for event in reviewed_events if event["event_type"] == "high_risk_posture"
    )
    assert reviewed_high_risk["reviewed_assessment_types"] == ["reba"]
    reviewed_summary = client.get(
        f"/api/v1/sessions/{session.json()['id']}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reviewed_summary.json()["reviewed_event_count"] == 1

    invalid_rula = client.put(
        f"/api/v1/sessions/{session.json()['id']}/events/{high_risk_event['id']}/reviews/rula",
        headers={"Authorization": f"Bearer {token}"},
        json={"load_score": 0, "activity_score": 2, "wrist_twist_score": 1},
    )
    assert invalid_rula.status_code == 422

    db_session.execute(delete(Assessment))
    db_session.execute(delete(Activity))
    db_session.execute(delete(ErgonomicEvent))
    db_session.commit()
    rebuilt = client.get(
        f"/api/v1/sessions/{session.json()['id']}/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rebuilt.status_code == 200
    rebuilt_events = rebuilt.json()
    event_types = [event["event_type"] for event in rebuilt_events]
    assert event_types.count("worker_observed") == 1
    assert event_types.count("high_risk_posture") == 1
    rebuilt_high_risk = next(
        event for event in rebuilt_events if event["event_type"] == "high_risk_posture"
    )
    assert rebuilt_high_risk["status"] == "resolved"
    assert rebuilt_high_risk["duration_ms"] == 12000

    snapshot_paths = [snapshot.file_path for snapshot in db_session.scalars(select(Snapshot))]
    deleted = client.delete(
        f"/api/v1/sessions/{session.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 204
    db_session.expire_all()
    assert db_session.get(AssessmentSession, session.json()["id"]) is None
    assert list(db_session.scalars(select(Detection))) == []
    assert list(db_session.scalars(select(SessionWorker))) == []
    assert list(db_session.scalars(select(ErgonomicEvent))) == []
    assert list(db_session.scalars(select(Snapshot))) == []
    assert all(not Path(path).exists() for path in snapshot_paths)
