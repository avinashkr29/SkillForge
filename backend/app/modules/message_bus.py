from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import WebSocket

from app.models import WebSocketEnvelope


class WebSocketMessageBus:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def send(self, message_type: str, payload: Optional[Dict[str, Any]] = None, frame_id: Optional[int] = None) -> None:
        envelope = WebSocketEnvelope(type=message_type, payload=payload or {}, frame_id=frame_id)
        await self.websocket.send_json(envelope.model_dump(mode="json"))
