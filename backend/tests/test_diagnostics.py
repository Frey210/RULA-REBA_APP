import json
from io import BytesIO
from zipfile import ZipFile

from app.core.security import create_access_token
from test_websocket_hub import recording  # noqa: F401


def test_diagnostics_is_authenticated_scoped_and_contains_no_secrets(client, recording):
    assert client.get('/api/v1/diagnostics').status_code == 401
    def export(user):
        response = client.get('/api/v1/diagnostics', headers={"Authorization": f"Bearer {create_access_token(user.id)}"})
        assert response.status_code == 200
        with ZipFile(BytesIO(response.content)) as archive:
            return json.loads(archive.read('diagnostics.json'))
    owner = export(recording[0])
    assert owner['cameras'][0]['cam_id'] == recording[2].cam_id
    assert owner['recording']['session_count'] == 1
    assert owner['storage']['automatic_raw_deletion'] is False
    other = export(recording[1])
    assert other['cameras'] == [] and other['recording']['session_count'] == 0
    serialized = json.dumps(owner)
    for secret in (recording[0].email, recording[4], 'credential_nonce', 'password_hash', 'edge_base_url'):
        assert secret not in serialized
