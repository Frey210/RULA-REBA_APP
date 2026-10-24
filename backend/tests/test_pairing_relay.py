import httpx
import pytest

from app.core.security import create_access_token
from app.models.camera_node import CameraNode
from app.models.user import User


@pytest.fixture
def pairing_request(db_session):
    user = User(email="pairing@test.local", username="pairing", password_hash="unused")
    db_session.add(user)
    db_session.flush()
    camera = CameraNode(cam_id="CAM_02", owner_user_id=user.id, metadata_json={},
                        node_credential_hash="legacy-credential")
    db_session.add(camera)
    db_session.commit()
    return {"headers": {"Authorization": f"Bearer {create_access_token(user.id)}"}, "json": {
        "cam_id": "CAM_02", "pairing_code": "123456", "edge_base_url": "http://edge.test:8765",
        "backend_url": "http://10.55.0.125:8000"}}


def test_legacy_agent_is_explained_before_pairing(client, pairing_request, monkeypatch, db_session):
    calls = []

    def request(method, url, **kwargs):
        calls.append(method)
        return httpx.Response(200, json={"service": "ergoquipt-edge", "cam_id": "CAM_02", "paired": True},
                              request=httpx.Request(method, url))

    monkeypatch.setattr("app.services.edge_devices.edge_http.request", request)
    response = client.post("/api/v1/device-pairings/relay", **pairing_request)
    assert response.status_code == 409
    assert "outdated" in response.json()["detail"]
    assert "Do not delete" in response.json()["detail"]
    assert calls == ["GET"]
    assert db_session.query(CameraNode).one().node_credential_hash == "legacy-credential"


@pytest.mark.parametrize("upstream,expected", [(403, "original owning backend"), (404, "expired"),
                                                  (409, "conflicts"), (422, "formats"), (500, "firewall")])
def test_pairing_errors_are_actionable_without_leaking_response(client, pairing_request, monkeypatch, upstream, expected):
    def request(method, url, **kwargs):
        if method == "GET":
            return httpx.Response(200, json={"service": "ergoquipt-edge", "cam_id": "CAM_02",
                "device_id": "00000000-0000-4000-8000-000000000002"}, request=httpx.Request(method, url))
        assert kwargs["headers"] == {}  # Legacy backend hashes are not usable Bearer credentials.
        return httpx.Response(upstream, text="private upstream diagnostic", request=httpx.Request(method, url))

    monkeypatch.setattr("app.services.edge_devices.edge_http.request", request)
    response = client.post("/api/v1/device-pairings/relay", **pairing_request)
    assert response.status_code == 409
    assert expected in response.json()["detail"]
    assert "private upstream" not in response.text


def test_pairing_network_failure_is_not_reported_as_bad_code(client, pairing_request, monkeypatch):
    def request(method, url, **kwargs):
        raise httpx.ConnectError("unreachable", request=httpx.Request(method, url))

    monkeypatch.setattr("app.services.edge_devices.edge_http.request", request)
    response = client.post("/api/v1/device-pairings/relay", **pairing_request)
    assert response.status_code == 503
    assert "LAN connection" in response.json()["detail"]


def test_upgraded_agent_can_replace_legacy_pairing(client, pairing_request, monkeypatch, db_session):
    code = client.post("/api/v1/device-pairings", headers=pairing_request["headers"]).json()["pairing_code"]
    pairing_request["json"]["pairing_code"] = code
    identity = "00000000-0000-4000-8000-000000000002"

    def request(method, url, **kwargs):
        if method == "GET":
            return httpx.Response(200, json={"service": "ergoquipt-edge", "cam_id": "CAM_02",
                "device_id": identity}, request=httpx.Request(method, url))
        assert kwargs["headers"] == {}
        completed = client.post("/api/v1/device-pairings/complete", json={
            "pairing_code": kwargs["json"]["pairing_code"], "cam_id": "CAM_02", "device_id": identity,
            "metadata": {"edge_base_url": pairing_request["json"]["edge_base_url"]}})
        assert completed.status_code == 200
        assert completed.json()["device_token"]
        return httpx.Response(200, json={"status": "paired", "cam_id": "CAM_02"},
                              request=httpx.Request(method, url))

    monkeypatch.setattr("app.services.edge_devices.edge_http.request", request)
    response = client.post("/api/v1/device-pairings/relay", **pairing_request)
    assert response.status_code == 200
    assert response.json() == {"status": "paired", "cam_id": "CAM_02"}
    camera = db_session.query(CameraNode).one()
    db_session.refresh(camera)
    assert camera.metadata_json["device_id"] == identity
    assert camera.node_credential_hash != "legacy-credential"
