from __future__ import annotations

import asyncio
import logging
import os

import asyncpg

logger = logging.getLogger("viewsense.database")


async def create_pool_with_retry(dsn: str, *, min_size: int = 1, max_size: int = 5) -> asyncpg.Pool:
    """Create a database pool with a bounded startup retry and no credential logging."""
    attempts = max(1, int(os.getenv("VS_DATABASE_CONNECT_ATTEMPTS", "12")))
    for attempt in range(1, attempts + 1):
        try:
            return await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size)
        except (OSError, asyncpg.PostgresError):
            if attempt == attempts:
                raise
            logger.warning(
                "database_connect_retry",
                extra={"event": "database_connect", "outcome": "retry"},
            )
            await asyncio.sleep(min(0.5 * attempt, 5.0))
    raise RuntimeError("database pool retry loop ended unexpectedly")
