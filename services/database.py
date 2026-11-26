import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://hanzala1000:hanzala1000@cluster0.powru.mongodb.net/")
DB_NAME = "always_together"

client: Optional[AsyncIOMotorClient] = None

def get_db():
    return client[DB_NAME]

def get_users(): return get_db()["users"]
def get_messages(): return get_db()["messages"]
def get_conversations(): return get_db()["conversations"]
def get_fcm_tokens(): return get_db()["fcm_tokens"]
def get_media(): return get_db()["chat_media"]

async def connect_db():
    global client
    client = AsyncIOMotorClient(MONGODB_URI)
    db = get_db()
    await db["users"].create_index("tag", unique=True)
    await db["users"].create_index("email", unique=True)
    await db["messages"].create_index([("conversation_id", 1), ("created_at", -1)])
    await db["messages"].create_index("deleted_at")
    await db["conversations"].create_index("participants")
    await db["fcm_tokens"].create_index("user_id", unique=True)
    print("[DB] Connected. Indexes ensured.")

async def close_db():
    global client
    if client:
        client.close()
