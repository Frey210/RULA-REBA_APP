from typing import Any
import asyncio

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy import or_, select

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.schemas.edge import EdgeDetectionEvent, WebSocketAck, WebSocketError
from app.services.detection_ingest import persist_detection_event, recording_write_lock
from app.services.live_hub import live_hub
from app.services.edge_devices import authenticate_device
from app.models.session import Session as AssessmentSession
from app.models.user import User

ws_router = APIRouter()


@ws_router.websocket("/ws/v1/edge/{cam_id}")
async def edge_ingest(websocket: WebSocket, cam_id: str) -> None:
    try:
        with SessionLocal() as db:
            authenticate_device(db, cam_id, websocket.headers.get("authorization"))
    except ValueError:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    while True:
        try:
            payload = await websocket.receive_json()
        except WebSocketDisconnect:
            return

        event_type = payload.get("event_type")
        try:
            if event_type == "detection":
                event = EdgeDetectionEvent.model_validate(payload)
                if event.cam_id != cam_id:
                    await websocket.send_json(
                        WebSocketError(
                            code="CAM_ID_MISMATCH",
                            detail="Path cam_id does not match payload cam_id",
                        ).model_dump()
                    )
                    continue
                inserted = await asyncio.to_thread(_persist_event, event, websocket.headers.get("authorization"))
                await websocket.send_json(WebSocketAck().model_dump())
                if inserted >= 0:
                    await live_hub.broadcast_session(event.session_id, _desktop_detection_event(event))
                continue

            await websocket.send_json(
                WebSocketError(code="UNKNOWN_EVENT_TYPE", detail=f"Unsupported event_type: {event_type}").model_dump()
            )
        except (ValidationError, ValueError) as exc:
            await websocket.send_json(
                        WebSocketError(code="INVALID_EVENT", detail=str(exc)).model_dump()
            )


@ws_router.websocket("/ws/v1/sessions/{session_id}/live")
async def session_live(websocket: WebSocket, session_id: str) -> None:
    token = websocket.headers.get("authorization", "").removeprefix("Bearer ")
    if not token:
        await websocket.accept()
        try:
            token = (await asyncio.wait_for(websocket.receive_json(), timeout=5)).get("token")
        except (asyncio.TimeoutError, ValueError, WebSocketDisconnect):
            await websocket.close(code=1008)
            return
    channel = _owned_live_channel(session_id, token)
    if channel is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await live_hub.connect_session(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_hub.disconnect_session(channel, websocket)


def _owned_live_channel(session_id: str, token: str | None) -> str | None:
    if not token:
        return None
    try:
        claims = decode_access_token(token)
        with SessionLocal() as db:
            user = db.get(User, claims.get("sub"))
            session = db.scalar(select(AssessmentSession).where(or_(AssessmentSession.id == session_id, AssessmentSession.session_code == session_id)))
            if claims.get("type") == "access" and user and user.is_active and session and session.owner_user_id == user.id:
                return session.session_code
    except jwt.PyJWTError:
        return None
    return None


def _persist_event(event: EdgeDetectionEvent, authorization: str | None) -> int:
    with recording_write_lock, SessionLocal() as db:
        authenticate_device(db, event.cam_id, authorization)
        return persist_detection_event(db, event)


def _desktop_detection_event(event: EdgeDetectionEvent) -> dict[str, Any]:
    return {
        "schema_version": event.schema_version,
        "event_type": "session_detection",
        "session_id": event.session_id,
        "cam_id": event.cam_id,
        "timestamp": event.timestamp,
        "frame_id": event.frame_id,
        "run_id": event.run_id,
        "detections": [detection.model_dump() for detection in event.detections],
    }
