import httpx
import pytest

from app.core.security import create_access_token
from test_websocket_hub import recording  # noqa: F401


def test_backend_check_requires_existing_device_secret(client, recording):
    assert client.get('/api/v1/device-pairings/check/CAM_01').status_code == 403
    response = client.get('/api/v1/device-pairings/check/CAM_01', headers={'Authorization': 'Bearer ' + recording[4]})
    assert response.status_code == 200
    assert response.json()['device_id'] == recording[2].metadata_json['device_id']
    assert recording[4] not in response.text


@pytest.mark.parametrize('failure', [None, 'identity', 'callback'])
def test_reconnect_preserves_pairing_and_commits_only_verified_connection(client, recording, db_session, monkeypatch, failure):
    user, _, camera, session, secret = recording
    session.status = 'completed'
    db_session.commit()
    old = dict(camera.metadata_json)
    calls = []
    def request(method, url, **kwargs):
        calls.append((url, kwargs.get('json')))
        identity = 'wrong-device' if failure == 'identity' else old['device_id']
        status = 409 if failure == 'callback' and url.endswith('/network/reconnect') else 200
        data = {'cam_id': 'CAM_01', 'device_id': identity, 'status': 'connected', 'camera_available': True}
        return httpx.Response(status, json=data, headers={'x-device-id': identity}, request=httpx.Request(method, url))
    monkeypatch.setattr('app.services.edge_devices.edge_http.request', request)
    monkeypatch.setattr('app.api.v1.routes.camera_nodes.backend_url_for_edge', lambda _: 'http://192.168.10.50:8000')
    response = client.post(f'/api/v1/camera-nodes/{camera.id}/reconnect',
        json={'edge_base_url': 'http://192.168.10.80:8765'}, headers={'Authorization': 'Bearer ' + create_access_token(user.id)})
    db_session.refresh(camera)
    if failure:
        assert response.status_code == 409
        assert camera.metadata_json == old
    else:
        assert response.status_code == 200
        assert camera.metadata_json['edge_base_url'] == 'http://192.168.10.80:8765'
        assert camera.metadata_json['credential_nonce'] == old['credential_nonce']
        assert any(payload == {'backend_url': 'http://192.168.10.50:8000'} for _, payload in calls)
    assert secret not in response.text


def test_network_changes_block_other_owners_and_active_sessions(client, recording):
    owner, other, camera, _, _ = recording
    path = f'/api/v1/camera-nodes/{camera.id}'
    for suffix, payload in [('/reconnect', {'edge_base_url': 'http://new.test'}),
                            ('/network/ethernet', {'mode': 'site'}),
                            ('/network/wifi/connect', {'ssid': 'Factory', 'password': 'testpassword'})]:
        assert client.post(path + suffix, json=payload, headers={'Authorization': 'Bearer ' + create_access_token(owner.id)}).status_code == 409
        assert client.post(path + suffix, json=payload, headers={'Authorization': 'Bearer ' + create_access_token(other.id)}).status_code == 404
