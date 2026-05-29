import random
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from database import get_session
from models import Key, Channel

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


class KeyResponse(BaseModel):
    id: int
    value: str
    channel_id: int
    channel_name: Optional[str] = None
    status: str
    weight: int
    last_used: Optional[str] = None
    last_check: Optional[str] = None
    error_count: int
    quota_remaining: Optional[float] = None
    total_requests: int
    success_requests: int
    avg_response_time: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[KeyResponse])
async def list_keys(
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(Key).order_by(Key.id)
    if channel_id:
        q = q.where(Key.channel_id == channel_id)
    if status:
        q = q.where(Key.status == status)
    result = await session.execute(q)
    keys = result.scalars().all()
    responses = []
    for k in keys:
        ch = await session.get(Channel, k.channel_id)
        responses.append(KeyResponse(
            id=k.id, value=k.value, channel_id=k.channel_id,
            channel_name=ch.name if ch else None,
            status=k.status, weight=k.weight,
            last_used=str(k.last_used) if k.last_used else None,
            last_check=str(k.last_check) if k.last_check else None,
            error_count=k.error_count,
            quota_remaining=k.quota_remaining,
            total_requests=k.total_requests,
            success_requests=k.success_requests,
            avg_response_time=k.avg_response_time,
            created_at=str(k.created_at) if k.created_at else None,
            updated_at=str(k.updated_at) if k.updated_at else None,
        ))
    return responses


@router.post("/", response_model=KeyResponse)
async def create_key(data: KeyCreate, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, data.channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    k = Key(value=data.value, channel_id=data.channel_id, weight=data.weight)
    session.add(k)
    await session.commit()
    await session.refresh(k)
    return KeyResponse(
        id=k.id, value=k.value, channel_id=k.channel_id,
        channel_name=ch.name,
        status=k.status, weight=k.weight,
        last_used=str(k.last_used) if k.last_used else None,
        last_check=str(k.last_check) if k.last_check else None,
        error_count=k.error_count,
        quota_remaining=k.quota_remaining,
        total_requests=k.total_requests,
        success_requests=k.success_requests,
        avg_response_time=k.avg_response_time,
        created_at=str(k.created_at) if k.created_at else None,
        updated_at=str(k.updated_at) if k.updated_at else None,
    )


@router.post("/batch", response_model=list[KeyResponse])
async def batch_create_keys(data: KeyBatchCreate, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, data.channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    # Parse keys: split by comma, newline, or whitespace
    raw_keys = data.keys.replace("\n", ",").replace("\r", ",").replace(" ", ",")
    key_values = [kv.strip() for kv in raw_keys.split(",") if kv.strip()]
    if not key_values:
        raise HTTPException(400, "No valid keys found in input")
    created = []
    for kv in key_values:
        existing = await session.execute(select(Key).where(Key.value == kv, Key.channel_id == data.channel_id))
        if existing.scalar_one_or_none():
            continue  # skip duplicates
        k = Key(value=kv, channel_id=data.channel_id, weight=data.weight)
        session.add(k)
        created.append(k)
    await session.commit()
    responses = []
    for k in created:
        await session.refresh(k)
        responses.append(KeyResponse(
            id=k.id, value=k.value, channel_id=k.channel_id,
            channel_name=ch.name,
            status=k.status, weight=k.weight,
            last_used=str(k.last_used) if k.last_used else None,
            last_check=str(k.last_check) if k.last_check else None,
            error_count=k.error_count,
            quota_remaining=k.quota_remaining,
            total_requests=k.total_requests,
            success_requests=k.success_requests,
            avg_response_time=k.avg_response_time,
            created_at=str(k.created_at) if k.created_at else None,
            updated_at=str(k.updated_at) if k.updated_at else None,
        ))
    return responses


@router.put("/{key_id}", response_model=KeyResponse)
async def update_key(key_id: int, data: KeyUpdate, session: AsyncSession = Depends(get_session)):
    k = await session.get(Key, key_id)
    if not k:
        raise HTTPException(404, "Key not found")
    update_data = data.model_dump(exclude_unset=True)
    for attr, val in update_data.items():
        setattr(k, attr, val)
    await session.commit()
    await session.refresh(k)
    ch = await session.get(Channel, k.channel_id)
    return KeyResponse(
        id=k.id, value=k.value, channel_id=k.channel_id,
        channel_name=ch.name if ch else None,
        status=k.status, weight=k.weight,
        last_used=str(k.last_used) if k.last_used else None,
        last_check=str(k.last_check) if k.last_check else None,
        error_count=k.error_count,
        quota_remaining=k.quota_remaining,
        total_requests=k.total_requests,
        success_requests=k.success_requests,
        avg_response_time=k.avg_response_time,
        created_at=str(k.created_at) if k.created_at else None,
        updated_at=str(k.updated_at) if k.updated_at else None,
    )


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
        # Pick the key with lowest total_requests; tie-break by last_used (oldest first)
        sorted_keys = sorted(active_keys, key=lambda k: (k.total_requests, k.last_used or datetime.min))
        return sorted_keys[0]

    else:
        return random.choice(active_keys)