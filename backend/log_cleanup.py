import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import delete
from database import async_session
from models import RequestLog
from config import LOG_RETENTION_DAYS

logger = logging.getLogger("log_cleanup")


async def run_log_cleanup():
    """Periodic log cleanup loop."""
    while True:
        try:
            cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
            async with async_session() as session:
                result = await session.execute(
                    delete(RequestLog).where(RequestLog.timestamp < cutoff)
                )
                await session.commit()
                if result.rowcount > 0:
                    logger.info(f"Cleaned up {result.rowcount} log entries older than {LOG_RETENTION_DAYS} days")
        except Exception as e:
            logger.error(f"Log cleanup error: {e}")

        # Run once per day
        await asyncio.sleep(86400)


async def start_log_cleanup():
    """Start the background log cleanup task."""
    asyncio.create_task(run_log_cleanup())
    logger.info(f"Log cleanup started (retention={LOG_RETENTION_DAYS} days)")