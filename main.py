import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson import ObjectId

from services.database import connect_db, close_db, get_users, get_conversations
from services.ws_manager import manager
from services.keepalive import keepalive_loop, cleanup_deleted_messages
from services.auth_service import decode_token
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.conversations import router as conversations_router
from routes.messages import router as messages_router
from routes.notifications import router as notifications_router, calls_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    keepalive_task = asyncio.create_task(keepalive_loop())
    cleanup_task   = asyncio.create_task(cleanup_deleted_messages())
    print("[Server] Always Together Backend started 🤝")
    yield
    keepalive_task.cancel()
    cleanup_task.cancel()
    await close_db()


app = FastAPI(
    title="Always Together Backend",
    description="Real-time chat: WebSockets · MongoDB · FCM · Translation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(conversations_router)
app.include_router(messages_router)
app.include_router(notifications_router)
app.include_router(calls_router)


@app.get("/ping")
async def ping():
    return {"status": "alive", "time": datetime.utcnow().isoformat()}


@app.get("/")
async def root():
    return {"app": "Always Together Backend 🤝", "status": "running", "docs": "/docs"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = None):
    # Auth check
    if not token:
        await websocket.close(code=4001); return
    try:
        payload = decode_token(token)
        if payload.get("sub") != user_id:
            await websocket.close(code=4003); return
    except HTTPException:
        await websocket.close(code=4001); return

    await manager.connect(user_id, websocket)
    users = get_users()
    try:
        await users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_online": True}})
    except Exception:
        pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg   = json.loads(raw)
                event = msg.get("event", "")
                data  = msg.get("data", {})

                if event in ("typing", "stop_typing"):
                    conv_id = data.get("conversation_id", "")
                    if conv_id:
                        convs = get_conversations()
                        try:
                            conv = await convs.find_one({"_id": ObjectId(conv_id)})
                            if conv:
                                for uid in conv.get("participants", []):
                                    if uid != user_id:
                                        await manager.send_to(uid, event,
                                            {"conversation_id": conv_id, "user_id": user_id})
                        except Exception:
                            pass
            except Exception:
                pass

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        try:
            await users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_online": False}})
        except Exception:
            pass
