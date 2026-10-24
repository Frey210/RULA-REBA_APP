from collections import defaultdict
import asyncio

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class LiveHub:
    def __init__(self) -> None:
        self._session_clients: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect_session(self, session_id: str, websocket: WebSocket) -> None:
        if websocket.application_state != WebSocketState.CONNECTED:
            await websocket.accept()
        self._session_clients[session_id].add(websocket)

    def disconnect_session(self, session_id: str, websocket: WebSocket) -> None:
        clients = self._session_clients.get(session_id)
        if not clients:
            return
        clients.discard(websocket)
        if not clients:
            self._session_clients.pop(session_id, None)

    async def broadcast_session(self, session_id: str, payload: dict) -> None:
        async def send(websocket):
            try:
                await asyncio.wait_for(websocket.send_json(payload), timeout=0.5)
            except (RuntimeError, OSError, asyncio.TimeoutError):
                self.disconnect_session(session_id, websocket)
        await asyncio.gather(*(send(ws) for ws in list(self._session_clients.get(session_id, set()))))


live_hub = LiveHub()

