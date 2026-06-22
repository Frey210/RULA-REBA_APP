from typing import Any

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.schemas.edge import EdgeDetectionEvent, EdgeHeartbeatEvent, WebSocketAck, WebSocketError
from app.services.detection_ingest import persist_detection_event
from app.services.live_hub import live_hub

ws_router = APIRouter()


@ws_router.websocket("/ws/v1/edge/{cam_id}")
async def edge_ingest(websocket: WebSocket, cam_id: str) -> None:
    await websocket.accept()
    while True:
        try:
            payload = await websocket.receive_json()
        except WebSocketDisconnect:
            return

        event_type = payload.get("event_type")
        try:
            if event_type == "heartbeat":
                EdgeHeartbeatEvent.model_validate(payload)
                await websocket.send_json(WebSocketAck().model_dump())
                continue

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
                _persist_event(event)
                await live_hub.broadcast_session(event.session_id, _desktop_detection_event(event))
                await websocket.send_json(WebSocketAck().model_dump())
                continue

            await websocket.send_json(
                WebSocketError(code="UNKNOWN_EVENT_TYPE", detail=f"Unsupported event_type: {event_type}").model_dump()
            )
        except ValidationError as exc:
            await websocket.send_json(
                WebSocketError(code="VALIDATION_ERROR", detail=str(exc.errors())).model_dump()
            )


@ws_router.websocket("/ws/v1/sessions/{session_id}/live")
async def session_live(websocket: WebSocket, session_id: str, token: str | None = None) -> None:
    if not _is_valid_access_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await live_hub.connect_session(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_hub.disconnect_session(session_id, websocket)


def _is_valid_access_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        decode_access_token(token)
    except jwt.PyJWTError:
        return False
    return True


def _persist_event(event: EdgeDetectionEvent) -> int:
    db: Session = SessionLocal()
    try:
        return persist_detection_event(db, event)
    finally:
        db.close()


def _desktop_detection_event(event: EdgeDetectionEvent) -> dict[str, Any]:
    return {
        "schema_version": event.schema_version,
        "event_type": "session_detection",
        "session_id": event.session_id,
        "cam_id": event.cam_id,
        "timestamp": event.timestamp,
        "frame_id": event.frame_id,
        "detections": [detection.model_dump() for detection in event.detections],
    }
