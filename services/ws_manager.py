from typing import Dict
from fastapi import WebSocket
import json


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}  # user_id -> websocket

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active[user_id] = ws
        print(f"[WS] Connected: {user_id} | Total: {len(self.active)}")

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)
        print(f"[WS] Disconnected: {user_id}")

    async def send_to(self, user_id: str, event: str, data: dict):
        ws = self.active.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps({"event": event, "data": data}))
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, user_ids: list, event: str, data: dict):
        for uid in user_ids:
            await self.send_to(uid, event, data)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active


manager = ConnectionManager()
