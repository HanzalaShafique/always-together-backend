"""
Run this ONCE to set up MongoDB indexes for Always Together.
Usage: python setup_mongodb.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://hanzala1000:hanzala1000@cluster0.powru.mongodb.net/"
)

async def setup():
    print("[Setup] Connecting to MongoDB Atlas...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client["always_together"]

    print("[Setup] Creating indexes...")
    await db.users.create_index("tag",   unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index([("tag", "text"), ("display_name", "text")])
    print("  ✓ users")

    await db.messages.create_index([("conversation_id", 1), ("created_at", -1)])
    await db.messages.create_index("deleted_at")
    await db.messages.create_index("sender_id")
    print("  ✓ messages")

    await db.conversations.create_index("participants")
    await db.conversations.create_index([("participants", 1), ("updated_at", -1)])
    print("  ✓ conversations")

    await db.fcm_tokens.create_index("user_id", unique=True)
    print("  ✓ fcm_tokens")

    print("\n✅ All MongoDB indexes created!")
    client.close()

if __name__ == "__main__":
    asyncio.run(setup())
