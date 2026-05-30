import asyncio
import logging
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select
from database import async_session
from models import Key, Channel
from config import HEALTH_CHECK_INTERVAL, HEALTH_CHECK_TIMEOUT, HEALTH_CHECK_MAX_ERRORS, PROXY_URL
from settings_store import get_key_cooldown_seconds

logger = logging.getLogger("health_check")


async def check_single_key(key: Key, channel: Channel) -> str:
    """Send a minimal request to verify key health."""
    url = channel.base_url.rstrip("/") + "/v1/models"
    headers = {"Authorization": f"Bearer {key.value}"}
    proxy = PROXY_URL if PROXY_URL else None

    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT, proxy=proxy) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return "healthy"
            elif resp.status_code == 401:
                logger.warning(f"Key {key.id} auth failed (401) for channel {channel.name}")
                return "unhealthy"
            elif resp.status_code == 429:
                # Rate limited but key is valid
                logger.info(f"Key {key.id} rate limited (429) for channel {channel.name}, cooling down")
                return "cooldown"
            else:
                logger.warning(f"Key {key.id} unexpected status {resp.status_code} for channel {channel.name}")
                return "unhealthy"
    except Exception as e:
        logger.error(f"Key {key.id} health check error: {e}")
        return "unhealthy"


async def run_health_checks():
    """Periodic health check loop."""
    while True:
        try:
            async with async_session() as session:
                result = await session.execute(select(Key).where(Key.status != "inactive"))
                keys = result.scalars().all()
                now = datetime.now()

                for key in keys:
                    if key.status == "cooldown":
                        if key.cooldown_until and key.cooldown_until > now:
                            continue
                        key.status = "active"
                        key.cooldown_until = None
                        key.error_count = 0
                        await session.commit()

                    channel = await session.get(Channel, key.channel_id)
                    if not channel or not channel.enabled:
                        continue

                    check_result = await check_single_key(key, channel)
                    key.last_check = now

                    if check_result == "healthy":
                        if key.status == "error" and key.error_count < HEALTH_CHECK_MAX_ERRORS:
                            # Recover from error if check passes
                            key.status = "active"
                            key.error_count = 0
                            key.cooldown_until = None
                    elif check_result == "cooldown":
                        cooldown_seconds = await get_key_cooldown_seconds(session)
                        key.status = "cooldown"
                        key.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
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
