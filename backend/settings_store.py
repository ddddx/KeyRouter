from sqlalchemy.ext.asyncio import AsyncSession

from config import KEY_COOLDOWN_SECONDS, MIN_KEY_COOLDOWN_SECONDS
from models import AppSetting

KEY_COOLDOWN_SETTING = "key_cooldown_seconds"


async def get_key_cooldown_seconds(session: AsyncSession) -> int:
    setting = await session.get(AppSetting, KEY_COOLDOWN_SETTING)
    if not setting:
        return KEY_COOLDOWN_SECONDS
    try:
        return max(MIN_KEY_COOLDOWN_SECONDS, int(setting.value))
    except (TypeError, ValueError):
        return KEY_COOLDOWN_SECONDS


async def set_key_cooldown_seconds(session: AsyncSession, seconds: int) -> int:
    seconds = max(MIN_KEY_COOLDOWN_SECONDS, int(seconds))
    setting = await session.get(AppSetting, KEY_COOLDOWN_SETTING)
    if setting:
        setting.value = str(seconds)
    else:
        session.add(AppSetting(key=KEY_COOLDOWN_SETTING, value=str(seconds)))
    await session.commit()
    return seconds
