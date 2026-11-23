"""Background cleanup: hard-delete messages soft-deleted more than 24 h ago."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_SECONDS = 3600  # run every hour
HARD_DELETE_AFTER_HOURS = 24


async def _cleanup_once() -> None:
    from services.database import messages as msg_col

    cutoff = datetime.utcnow() - timedelta(hours=HARD_DELETE_AFTER_HOURS)
    result = await msg_col().delete_many(
        {"is_deleted": True, "deleted_at": {"$lte": cutoff}}
    )
    if result.deleted_count:
        logger.info("Cleanup: hard-deleted %d messages", result.deleted_count)


async def cleanup_loop() -> None:
    """Infinite loop – meant to be started as an asyncio task on app startup."""
    while True:
        try:
            await _cleanup_once()
        except Exception as exc:
            logger.exception("Cleanup task error: %s", exc)
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
