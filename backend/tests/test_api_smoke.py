from fastapi.testclient import TestClient


def register_and_login(client: TestClient, email: str = "operator@example.com") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "full_name": "Operator"},
    )
    assert response.status_code == 201

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strong-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_and_version(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/v1/version").json()["api_version"] == "1.0"


def test_auth_and_worker_scope(client: TestClient) -> None:
    token_a = register_and_login(client, "a@example.com")
    token_b = register_and_login(client, "b@example.com")

    response = client.post(
        "/api/v1/workers",
        headers=auth_header(token_a),
        json={"employee_number": "EMP-1", "name": "Worker A", "department": "Warehouse"},
    )
    assert response.status_code == 201

    assert len(client.get("/api/v1/workers", headers=auth_header(token_a)).json()) == 1
    assert client.get("/api/v1/workers", headers=auth_header(token_b)).json() == []


def test_pairing_and_session_lifecycle(client: TestClient) -> None:
    token = register_and_login(client)

    pairing_response = client.post("/api/v1/device-pairings", headers=auth_header(token))
    assert pairing_response.status_code == 201
    pairing_code = pairing_response.json()["pairing_code"]

    complete_response = client.post(
        "/api/v1/device-pairings/complete",
        json={
            "pairing_code": pairing_code,
            "cam_id": "CAM_01",
            "hostname": "ergoquipt-rr",
            "device_type": "raspberry_pi_5_hailo8",
            "metadata": {"hailort": "4.23.0"},
        },
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "paired"

    session_response = client.post(
        "/api/v1/sessions",
        headers=auth_header(token),
        json={"camera_node_ids": ["CAM_01"], "notes": "Smoke test"},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    start_response = client.post(f"/api/v1/sessions/{session_id}/start", headers=auth_header(token))
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"

    stop_response = client.post(f"/api/v1/sessions/{session_id}/stop", headers=auth_header(token))
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "review_pending"


def test_camera_node_rename_and_delete_are_user_scoped(client: TestClient) -> None:
    token_a = register_and_login(client, "device-a@example.com")
    token_b = register_and_login(client, "device-b@example.com")

    pairing_response = client.post("/api/v1/device-pairings", headers=auth_header(token_a))
    pairing_code = pairing_response.json()["pairing_code"]

    complete_response = client.post(
        "/api/v1/device-pairings/complete",
        json={
            "pairing_code": pairing_code,
            "cam_id": "CAM_01",
            "hostname": "ergoquipt-rr",
            "device_type": "raspberry_pi_5_hailo8",
            "metadata": {},
        },
    )
    assert complete_response.status_code == 200

    camera = client.get("/api/v1/camera-nodes", headers=auth_header(token_a)).json()[0]
    camera_id = camera["id"]

    forbidden = client.patch(
        f"/api/v1/camera-nodes/{camera_id}",
        headers=auth_header(token_b),
        json={"display_name": "Other user camera"},
    )
    assert forbidden.status_code == 404

    renamed = client.patch(
        f"/api/v1/camera-nodes/{camera_id}",
        headers=auth_header(token_a),
        json={"display_name": "Packing Station Camera"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["metadata_json"]["display_name"] == "Packing Station Camera"

    removed = client.delete(f"/api/v1/camera-nodes/{camera_id}", headers=auth_header(token_a))
    assert removed.status_code == 204
    assert client.get("/api/v1/camera-nodes", headers=auth_header(token_a)).json() == []


def test_scoring_preview_requires_auth_and_returns_score(client: TestClient) -> None:
    unauthenticated = client.post(
        "/api/v1/scoring/preview",
        json={
            "assessment_type": "reba",
            "angles": {"neck": 5, "trunk": 3, "ua_l": 10, "ua_r": 12, "la_l": 85, "la_r": 90},
            "manual": {"load_score": 0, "coupling_score": 0, "activity_score": 0},
        },
    )
    assert unauthenticated.status_code == 401

    token = register_and_login(client, "score@example.com")
    response = client.post(
        "/api/v1/scoring/preview",
        headers=auth_header(token),
        json={
            "assessment_type": "reba",
            "angles": {
                "neck": 5,
                "trunk": 3,
                "ua_l": 10,
                "ua_r": 12,
                "la_l": 85,
                "la_r": 90,
                "wrist_l": 4,
                "wrist_r": 5,
                "leg_l": 10,
                "leg_r": 12,
            },
            "manual": {"load_score": 0, "coupling_score": 0, "activity_score": 0},
        },
    )
    assert response.status_code == 200
    assert response.json()["assessment_type"] == "reba"
    assert response.json()["score"] >= 1
