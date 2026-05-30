from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional
from database import get_session
from models import Channel
from key_manager import recover_expired_cooldowns

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelCreate(BaseModel):
    name: str
    base_url: str
    strategy: str = "round_robin"
    enabled: bool = True
    weight: int = 1


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    strategy: Optional[str] = None
    enabled: Optional[bool] = None
    weight: Optional[int] = None


class ChannelResponse(BaseModel):
    id: int
    name: str
    base_url: str
    strategy: str
    enabled: bool
    weight: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    key_count: int = 0
    active_key_count: int = 0

    class Config:
        from_attributes = True


@router.get("", response_model=list[ChannelResponse], include_in_schema=False)
@router.get("/", response_model=list[ChannelResponse])
async def list_channels(session: AsyncSession = Depends(get_session)):
    await recover_expired_cooldowns(session)
    result = await session.execute(select(Channel).order_by(Channel.id))
    channels = result.scalars().all()
    responses = []
    for ch in channels:
        from sqlalchemy import func, select as s2
        from models import Key
        kc = await session.execute(s2(func.count(Key.id)).where(Key.channel_id == ch.id))
        akc = await session.execute(s2(func.count(Key.id)).where(Key.channel_id == ch.id, Key.status == "active"))
        responses.append(ChannelResponse(
            id=ch.id,
            name=ch.name,
            base_url=ch.base_url,
            strategy=ch.strategy,
            enabled=ch.enabled,
            weight=ch.weight,
            created_at=str(ch.created_at) if ch.created_at else None,
            updated_at=str(ch.updated_at) if ch.updated_at else None,
            key_count=kc.scalar() or 0,
            active_key_count=akc.scalar() or 0,
        ))
    return responses


@router.post("", response_model=ChannelResponse, include_in_schema=False)
@router.post("/", response_model=ChannelResponse)
async def create_channel(data: ChannelCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(Channel).where(Channel.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Channel name already exists")
    ch = Channel(name=data.name, base_url=data.base_url, strategy=data.strategy, enabled=data.enabled, weight=data.weight)
    session.add(ch)
    await session.commit()
    await session.refresh(ch)
    return ChannelResponse(
        id=ch.id, name=ch.name, base_url=ch.base_url, strategy=ch.strategy,
        enabled=ch.enabled, weight=ch.weight,
        created_at=str(ch.created_at) if ch.created_at else None,
        updated_at=str(ch.updated_at) if ch.updated_at else None,
        key_count=0, active_key_count=0,
    )


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: int, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    await recover_expired_cooldowns(session, channel_id)
    from sqlalchemy import func, select as s2
    from models import Key
    kc = await session.execute(s2(func.count(Key.id)).where(Key.channel_id == ch.id))
    akc = await session.execute(s2(func.count(Key.id)).where(Key.channel_id == ch.id, Key.status == "active"))
    return ChannelResponse(
        id=ch.id, name=ch.name, base_url=ch.base_url, strategy=ch.strategy,
        enabled=ch.enabled, weight=ch.weight,
        created_at=str(ch.created_at) if ch.created_at else None,
        updated_at=str(ch.updated_at) if ch.updated_at else None,
        key_count=kc.scalar() or 0, active_key_count=akc.scalar() or 0,
    )


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(channel_id: int, data: ChannelUpdate, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    await recover_expired_cooldowns(session, channel_id)
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(ch, k, v)
    await session.commit()
    await session.refresh(ch)
    from sqlalchemy import func, select as s2
    from models import Key
    kc = await session.execute(s2(func.count(Key.id)).where(Key.channel_id == ch.id))
    akc = await session.execute(s2(func.count(Key.id)).where(Key.channel_id == ch.id, Key.status == "active"))
    return ChannelResponse(
        id=ch.id, name=ch.name, base_url=ch.base_url, strategy=ch.strategy,
        enabled=ch.enabled, weight=ch.weight,
        created_at=str(ch.created_at) if ch.created_at else None,
        updated_at=str(ch.updated_at) if ch.updated_at else None,
        key_count=kc.scalar() or 0, active_key_count=akc.scalar() or 0,
    )


@router.delete("/{channel_id}")
async def delete_channel(channel_id: int, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, channel_id)
    if not ch:
        raise HTTPException(404, "Channel not found")
    await session.delete(ch)
    await session.commit()
    return {"message": "Channel deleted"}
