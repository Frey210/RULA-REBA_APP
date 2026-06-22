from fastapi.testclient import TestClient


def get_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "ws@example.com", "password": "strong-password", "full_name": "WS User"},
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

