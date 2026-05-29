import asyncio
import logging
from datetime import datetime
import httpx
from sqlalchemy import select
from database import async_session
from models import Key, Channel
from config import HEALTH_CHECK_INTERVAL, HEALTH_CHECK_TIMEOUT, HEALTH_CHECK_MAX_ERRORS, PROXY_URL

logger = logging.getLogger("health_check")


async def check_single_key(key: Key, channel: Channel) -> bool:
    """Send a minimal request to verify key health."""
    url = channel.base_url.rstrip("/") + "/v1/models"
    headers = {"Authorization": f"Bearer {key.value}"}
    proxy = PROXY_URL if PROXY_URL else None

    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT, proxy=proxy) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return True
            elif resp.status_code == 401:
                logger.warning(f"Key {key.id} auth failed (401) for channel {channel.name}")
                return False
            elif resp.status_code == 429:
                # Rate limited but key is valid
                logger.info(f"Key {key.id} rate limited (429) for channel {channel.name}")
                return True
            else:
                logger.warning(f"Key {key.id} unexpected status {resp.status_code} for channel {channel.name}")
                return False
    except Exception as e:
        logger.error(f"Key {key.id} health check error: {e}")
        return False


async def run_health_checks():
    """Periodic health check loop."""
    while True:
        try:
            async with async_session() as session:
                result = await session.execute(select(Key).where(Key.status != "inactive"))
                keys = result.scalars().all()

                for key in keys:
                    channel = await session.get(Channel, key.channel_id)
                    if not channel or not channel.enabled:
                        continue

                    is_healthy = await check_single_key(key, channel)
                    key.last_check = datetime.now()

                    if is_healthy:
                        if key.status == "error" and key.error_count < HEALTH_CHECK_MAX_ERRORS:
                            # Recover from error if check passes
                            key.status = "active"
                            key.error_count = 0
                    else:
                        key.error_count += 1
                        if key.error_count >= HEALTH_CHECK_MAX_ERRORS:
                            key.status = "error"

                    await session.commit()
        except Exception as e:
            logger.error(f"Health check cycle error: {e}")

        await asyncio.sleep(HEALTH_CHECK_INTERVAL)


async def start_health_checker():
    """Start the background health check task."""
    asyncio.create_task(run_health_checks())
    logger.info(f"Health checker started (interval={HEALTH_CHECK_INTERVAL}s, max_errors={HEALTH_CHECK_MAX_ERRORS})")