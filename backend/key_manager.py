import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from pydantic import BaseModel
from typing import Optional
from database import get_session
from models import Key, Channel, RequestLog

router = APIRouter(prefix="/api/keys", tags=["keys"])


class KeyCreate(BaseModel):
    value: str
    channel_id: int
    weight: int = 1


class KeyBatchCreate(BaseModel):
    keys: str  # comma or newline separated
    channel_id: int
    weight: int = 1


class KeyUpdate(BaseModel):
    status: Optional[str] = None
    weight: Optional[int] = None


def mask_key(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return val
    return val[:8] + "***"


class KeyResponse(BaseModel):
    id: int
    value: str
    value_masked: str
    channel_id: int
    channel_name: Optional[str] = None
    status: str
    weight: int
    last_used: Optional[str] = None
    last_check: Optional[str] = None
    cooldown_until: Optional[str] = None
    error_count: int
    quota_remaining: Optional[float] = None
    total_requests: int
    success_requests: int
    failed_requests: int
    avg_response_time_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    success_rate: float
    last_call: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


async def get_last_call(session: AsyncSession, key_id: int) -> Optional[dict]:
    result = await session.execute(
        select(RequestLog).where(RequestLog.key_id == key_id).order_by(desc(RequestLog.id)).limit(1)
    )
    log = result.scalar_one_or_none()
    if not log:
        return None
    return {
        "id": log.id,
        "timestamp": str(log.timestamp) if log.timestamp else None,
        "model": log.model,
        "prompt_tokens": log.prompt_tokens or 0,
        "completion_tokens": log.completion_tokens or 0,
        "total_tokens": (log.prompt_tokens or 0) + (log.completion_tokens or 0),
        "response_time_ms": log.response_time_ms or 0,
        "status_code": log.status_code,
        "error_code": log.error_code,
        "error_message": log.error_message,
        "is_success": log.is_success,
        "is_streaming": log.is_streaming,
        "source_ip": log.source_ip,
    }


async def recover_expired_cooldowns(session: AsyncSession, channel_id: Optional[int] = None) -> int:
    """Move expired cooldown keys back to active status."""
    now = datetime.now()
    q = select(Key).where(
        Key.status == "cooldown",
        or_(Key.cooldown_until == None, Key.cooldown_until <= now),
    )
    if channel_id is not None:
        q = q.where(Key.channel_id == channel_id)

    result = await session.execute(q)
    keys = result.scalars().all()
    for key in keys:
        key.status = "active"
        key.cooldown_until = None
        key.error_count = 0

    if keys:
        await session.commit()
    return len(keys)


def make_key_response(k: Key, ch_name: str = None, last_call: Optional[dict] = None) -> KeyResponse:
    return KeyResponse(
        id=k.id,
        value=k.value,
        value_masked=mask_key(k.value),
        channel_id=k.channel_id,
        channel_name=ch_name,
        status=k.status,
        weight=k.weight,
        last_used=str(k.last_used) if k.last_used else None,
        last_check=str(k.last_check) if k.last_check else None,
        cooldown_until=str(k.cooldown_until) if k.cooldown_until else None,
        error_count=k.error_count,
        quota_remaining=k.quota_remaining,
        total_requests=k.total_requests,
        success_requests=k.success_requests,
        failed_requests=k.failed_requests,
        avg_response_time_ms=round(k.avg_response_time, 1),
        total_prompt_tokens=k.total_prompt_tokens,
        total_completion_tokens=k.total_completion_tokens,
        total_tokens=k.total_prompt_tokens + k.total_completion_tokens,
        success_rate=round(k.success_requests / k.total_requests * 100, 2) if k.total_requests > 0 else 0,
        last_call=last_call,
        created_at=str(k.created_at) if k.created_at else None,
        updated_at=str(k.updated_at) if k.updated_at else None,
    )


@router.get("", response_model=list[KeyResponse], include_in_schema=False)
@router.get("/", response_model=list[KeyResponse])
async def list_keys(
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    await recover_expired_cooldowns(session, channel_id)
    q = select(Key).order_by(Key.id)
    if channel_id:
        q = q.where(Key.channel_id == channel_id)
    if status:
        q = q.where(Key.status == status)
    result = await session.execute(q)
    keys = result.scalars().all()
    responses = []
    # Pre-load channels
    channels_cache = {}
    for k in keys:
        if k.channel_id not in channels_cache:
            ch = await session.get(Channel, k.channel_id)
            channels_cache[k.channel_id] = ch
        ch_name = channels_cache[k.channel_id]
        ch_name = ch_name.name if ch_name else None
        responses.append(make_key_response(k, ch_name, await get_last_call(session, k.id)))
    return responses


@router.post("", response_model=KeyResponse, include_in_schema=False)
@router.post("/", response_model=KeyResponse)
async def create_key(data: KeyCreate, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, data.channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    k = Key(value=data.value, channel_id=data.channel_id, weight=data.weight)
    session.add(k)
    await session.commit()
    await session.refresh(k)
    return make_key_response(k, ch.name, await get_last_call(session, k.id))


@router.post("/batch", response_model=list[KeyResponse])
async def batch_create_keys(data: KeyBatchCreate, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, data.channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    raw_keys = data.keys.replace("\n", ",").replace("\r", ",").replace(" ", ",")
    key_values = [kv.strip() for kv in raw_keys.split(",") if kv.strip()]
    if not key_values:
        raise HTTPException(400, "No valid keys found in input")
    created = []
    for kv in key_values:
        existing = await session.execute(select(Key).where(Key.value == kv, Key.channel_id == data.channel_id))
        if existing.scalar_one_or_none():
            continue
        k = Key(value=kv, channel_id=data.channel_id, weight=data.weight)
        session.add(k)
        created.append(k)
    await session.commit()
    responses = []
    for k in created:
        await session.refresh(k)
        responses.append(make_key_response(k, ch.name, await get_last_call(session, k.id)))
    return responses


@router.put("/{key_id}", response_model=KeyResponse)
async def update_key(key_id: int, data: KeyUpdate, session: AsyncSession = Depends(get_session)):
    k = await session.get(Key, key_id)
    if not k:
        raise HTTPException(404, "Key not found")
    update_data = data.model_dump(exclude_unset=True)
    for attr, val in update_data.items():
        setattr(k, attr, val)
    if data.status == "active":
        k.cooldown_until = None
        k.error_count = 0
    await session.commit()
    await session.refresh(k)
    ch = await session.get(Channel, k.channel_id)
    return make_key_response(k, ch.name if ch else None, await get_last_call(session, k.id))


@router.delete("/{key_id}")
async def delete_key(key_id: int, session: AsyncSession = Depends(get_session)):
    k = await session.get(Key, key_id)
    if not k:
        raise HTTPException(404, "Key not found")
    await session.delete(k)
    await session.commit()
    return {"message": "Key deleted"}


@router.delete("/batch")
async def batch_delete_keys(
    channel_id: int,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(Key).where(Key.channel_id == channel_id)
    if status:
        q = q.where(Key.status == status)
    result = await session.execute(q)
    keys = result.scalars().all()
    for k in keys:
        await session.delete(k)
    await session.commit()
    return {"message": f"Deleted {len(keys)} keys"}


# ---- Key selection algorithms ----

_round_robin_counters: dict[int, int] = {}


async def select_key(channel_id: int, strategy: str, session: AsyncSession) -> Optional[Key]:
    """Select a key based on the channel's routing strategy."""
    await recover_expired_cooldowns(session, channel_id)

    result = await session.execute(
        select(Key).where(Key.channel_id == channel_id, Key.status == "active")
    )
    active_keys = result.scalars().all()
    if not active_keys:
        return None

    if strategy == "round_robin":
        idx = _round_robin_counters.get(channel_id, 0) % len(active_keys)
        _round_robin_counters[channel_id] = idx + 1
        return active_keys[idx]

    elif strategy == "weighted":
        total_weight = sum(k.weight for k in active_keys)
        r = random.randint(1, total_weight)
        cumulative = 0
        for k in active_keys:
            cumulative += k.weight
            if r <= cumulative:
                return k
        return active_keys[-1]

    elif strategy == "random":
        return random.choice(active_keys)

    elif strategy == "least_used":
        sorted_keys = sorted(active_keys, key=lambda k: (k.total_requests, k.last_used or datetime.min))
        return sorted_keys[0]

    else:
        return random.choice(active_keys)
