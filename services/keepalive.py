import asyncio
import os
import httpx
from datetime import datetime, timedelta
from services.database import get_messages

SPACE_URL = os.getenv("SPACE_URL", "https://hanzala1000-always-together-backend.hf.space")
PING_INTERVAL = 5 * 60  # 5 minutes


async def keepalive_loop():
    """Ping self every 5 minutes to keep HuggingFace Space alive."""
    await asyncio.sleep(10)  # Wait for server to fully start
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{SPACE_URL}/ping", timeout=10)
                print(f"[KeepAlive] Ping: {r.status_code} at {datetime.utcnow().isoformat()}")
        except Exception as e:
            print(f"[KeepAlive] Ping failed: {e}")
        await asyncio.sleep(PING_INTERVAL)


async def cleanup_deleted_messages():
    """Every hour: hard-delete messages soft-deleted >24h ago."""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            collection = get_messages()
            result = await collection.delete_many({
                "is_deleted": True,
                "deleted_at": {"$lt": cutoff}
            })
            if result.deleted_count > 0:
                print(f"[Cleanup] Hard-deleted {result.deleted_count} messages")
        except Exception as e:
            print(f"[Cleanup] Error: {e}")
