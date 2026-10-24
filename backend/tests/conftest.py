import os
from collections.abc import Generator

import pytest
import httpx
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

os.environ["DATABASE_URL"] = "sqlite://"

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


def override_get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def edge_stub(monkeypatch):
    state = {"running": False, "ready": False, "cam_id": "CAM_01", "camera_available": True}
    device_id = "00000000-0000-4000-8000-000000000001"
    buffer = BytesIO()
    Image.new("RGB", (640, 360), color=(20, 90, 84)).save(buffer, "JPEG")

    def request(method, url, **kwargs):
        payload = kwargs.get("json", {})
        if url.endswith("/detection/start"):
            state.update(payload, running=True, ready=True)
        if url.endswith("/detection/stop"):
            state.update(running=False, ready=False)
        headers = {"x-device-id": device_id}
        if "/snapshot/frames/" in url:
            headers.update({"content-type": "image/jpeg", "x-frame-id": url.rsplit("/", 1)[1],
                            "x-run-id": kwargs["params"]["run_id"]})
            return httpx.Response(200, content=buffer.getvalue(), headers=headers, request=httpx.Request(method, url))
        return httpx.Response(200, json=state, headers=headers, request=httpx.Request(method, url))

    monkeypatch.setattr("app.services.edge_devices.edge_http.request", request)
    return state
