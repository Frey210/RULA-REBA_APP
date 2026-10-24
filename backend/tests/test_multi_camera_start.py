import threading
from datetime import UTC, datetime

import httpx
import pytest

from app.core.security import create_access_token
from app.models.camera_node import CameraNode
from app.services.edge_devices import issue_device_token
from test_websocket_hub import recording  # noqa: F401


@pytest.mark.parametrize("lose_lease", [False, True])
def test_parallel_start_renews_ready_cameras_and_rolls_back_failure(client, recording, db_session, monkeypatch, lose_lease):
    camera = CameraNode(cam_id="CAM_02", owner_user_id=recording[0].id, metadata_json={
        "edge_base_url": "http://second.test", "device_id": "00000000-0000-4000-8000-000000000002"})
    db_session.add(camera)
    db_session.flush()
    issue_device_token(camera)
    session = recording[3]
    session.status = "created"
    session.metadata_json = {"camera_node_ids": [recording[2].cam_id, camera.cam_id]}
    db_session.commit()
    states = {"http://edge.test": {"cam_id": "CAM_01", "device_id": recording[2].metadata_json["device_id"]},
              "http://second.test": {"cam_id": "CAM_02", "device_id": camera.metadata_json["device_id"]}}
    barrier = threading.Barrier(2)
    renewals, stops = set(), set()

    def request(method, url, **kwargs):
        address = url.rsplit("/", 2)[0]
        state = states[address]
        if url.endswith("/detection/start"):
            anchor = kwargs["json"]["backend_timestamp_ms"]
            assert abs(anchor - datetime.now(UTC).timestamp() * 1000) < 2000
            barrier.wait(timeout=3)
            state.update(kwargs["json"], running=True, ready=True)
        if url.endswith("/detection/lease"):
            renewals.add(state["cam_id"])
            if lose_lease and state["cam_id"] == "CAM_02":
                return httpx.Response(409, headers={"x-device-id": state["device_id"]}, request=httpx.Request(method, url))
        if url.endswith("/detection/stop"):
            stops.add(state["cam_id"])
            state.update(running=False, ready=False)
        return httpx.Response(200, json={**state, "camera_available": True},
            headers={"x-device-id": state["device_id"]}, request=httpx.Request(method, url))
    monkeypatch.setattr("app.services.edge_devices.edge_http.request", request)
    response = client.post(f"/api/v1/sessions/{session.id}/start",
        headers={"Authorization": f"Bearer {create_access_token(recording[0].id)}"})
    assert response.status_code == (503 if lose_lease else 200), response.text
    assert renewals == {"CAM_01", "CAM_02"}
    db_session.refresh(session)
    assert session.status == ("failed" if lose_lease else "running")
    if lose_lease:
        assert stops == {"CAM_01", "CAM_02"}
