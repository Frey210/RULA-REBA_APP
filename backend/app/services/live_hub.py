from collections import defaultdict

from fastapi import WebSocket


class LiveHub:
    def __init__(self) -> None:
        self._session_clients: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect_session(self, session_id: str, websocket: WebSocket) -> None:
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
        disconnected: list[WebSocket] = []
        for websocket in list(self._session_clients.get(session_id, set())):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect_session(session_id, websocket)


live_hub = LiveHub()

