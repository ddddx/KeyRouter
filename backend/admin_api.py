from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from database import get_session
from models import Channel, Key, RequestLog
from config import HEALTH_CHECK_INTERVAL, HEALTH_CHECK_MAX_ERRORS, MAX_RETRY_COUNT, PORT, HOST, PROXY_URL

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats/dashboard")
async def dashboard_stats(session: AsyncSession = Depends(get_session)):
    total_requests = await session.execute(select(func.count(RequestLog.id)))
    success_requests = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.status_code < 400)
    )
    total_channels = await session.execute(select(func.count(Channel.id)))
    active_channels = await session.execute(
        select(func.count(Channel.id)).where(Channel.enabled == True)
    )
    total_keys = await session.execute(select(func.count(Key.id)))
    active_keys = await session.execute(
        select(func.count(Key.id)).where(Key.status == "active")
    )
    error_keys = await session.execute(
        select(func.count(Key.id)).where(Key.status == "error")
    )
    avg_response = await session.execute(
        select(func.avg(RequestLog.response_time)).where(RequestLog.status_code < 400)
    )
    total_tokens = await session.execute(
        select(func.sum(RequestLog.prompt_tokens) + func.sum(RequestLog.completion_tokens))
    )
    error_rate = 0.0
    tr = total_requests.scalar() or 0
    sr = success_requests.scalar() or 0
    if tr > 0:
        error_rate = round((tr - sr) / tr * 100, 2)

    # Recent errors (last 10)
    recent_errors = await session.execute(
        select(RequestLog).where(RequestLog.status_code >= 400).order_by(desc(RequestLog.id)).limit(10)
    )
    errors = []
    for e in recent_errors.scalars().all():
        ch_name = None
        key_value = None
        if e.channel_id:
            ch = await session.get(Channel, e.channel_id)
            ch_name = ch.name if ch else None
        if e.key_id:
            k = await session.get(Key, e.key_id)
            key_value = k.value[:20] + "..." if k else None
        errors.append({
            "timestamp": str(e.timestamp) if e.timestamp else None,
            "channel": ch_name,
            "key": key_value,
            "model": e.model,
            "status_code": e.status_code,
            "error_message": e.error_message,
        })

    return {
        "total_requests": tr,
        "success_requests": sr,
        "error_rate": error_rate,
        "total_channels": total_channels.scalar() or 0,
        "active_channels": active_channels.scalar() or 0,
        "total_keys": total_keys.scalar() or 0,
        "active_keys": active_keys.scalar() or 0,
        "error_keys": error_keys.scalar() or 0,
        "avg_response_time": round(avg_response.scalar() or 0, 3),
        "total_tokens": total_tokens.scalar() or 0,
        "recent_errors": errors,
    }


@router.get("/stats/channel/{channel_id}")
async def channel_stats(channel_id: int, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, channel_id)
    if not ch:
        return {"error": "Channel not found"}

    total_requests = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.channel_id == channel_id)
    )
    success_requests = await session.execute(
        select(func.count(RequestLog.id)).where(
            RequestLog.channel_id == channel_id, RequestLog.status_code < 400
        )
    )
    avg_response = await session.execute(
        select(func.avg(RequestLog.response_time)).where(
            RequestLog.channel_id == channel_id, RequestLog.status_code < 400
        )
    )
    total_tokens = await session.execute(
        select(func.sum(RequestLog.prompt_tokens) + func.sum(RequestLog.completion_tokens))
        .where(RequestLog.channel_id == channel_id)
    )
    key_count = await session.execute(
        select(func.count(Key.id)).where(Key.channel_id == channel_id)
    )
    active_key_count = await session.execute(
        select(func.count(Key.id)).where(Key.channel_id == channel_id, Key.status == "active")
    )

    tr = total_requests.scalar() or 0
    sr = success_requests.scalar() or 0
    return {
        "channel_id": channel_id,
        "channel_name": ch.name,
        "total_requests": tr,
        "success_requests": sr,
        "error_rate": round((tr - sr) / tr * 100, 2) if tr > 0 else 0,
        "avg_response_time": round(avg_response.scalar() or 0, 3),
        "total_tokens": total_tokens.scalar() or 0,
        "key_count": key_count.scalar() or 0,
        "active_key_count": active_key_count.scalar() or 0,
    }


@router.get("/stats/key/{key_id}")
async def key_stats(key_id: int, session: AsyncSession = Depends(get_session)):
    k = await session.get(Key, key_id)
    if not k:
        return {"error": "Key not found"}

    total_requests = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.key_id == key_id)
    )
    success_requests = await session.execute(
        select(func.count(RequestLog.id)).where(
            RequestLog.key_id == key_id, RequestLog.status_code < 400
        )
    )
    avg_response = await session.execute(
        select(func.avg(RequestLog.response_time)).where(
            RequestLog.key_id == key_id, RequestLog.status_code < 400
        )
    )

    tr = total_requests.scalar() or 0
    sr = success_requests.scalar() or 0
    return {
        "key_id": key_id,
        "key_value": k.value[:20] + "...",
        "status": k.status,
        "total_requests": tr,
        "success_requests": sr,
        "success_rate": round(sr / tr * 100, 2) if tr > 0 else 0,
        "avg_response_time": round(avg_response.scalar() or 0, 3),
        "error_count": k.error_count,
        "key_total_requests": k.total_requests,
        "key_success_requests": k.success_requests,
    }


@router.get("/logs")
async def get_logs(
    channel_id: Optional[int] = None,
    key_id: Optional[int] = None,
    status_code: Optional[int] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    session: AsyncSession = Depends(get_session),
):
    q = select(RequestLog).order_by(desc(RequestLog.id))
    if channel_id:
        q = q.where(RequestLog.channel_id == channel_id)
    if key_id:
        q = q.where(RequestLog.key_id == key_id)
    if status_code:
        q = q.where(RequestLog.status_code == status_code)
    q = q.offset(offset).limit(limit)

    total_q = select(func.count(RequestLog.id))
    if channel_id:
        total_q = total_q.where(RequestLog.channel_id == channel_id)
    if key_id:
        total_q = total_q.where(RequestLog.key_id == key_id)
    if status_code:
        total_q = total_q.where(RequestLog.status_code == status_code)

    total = await session.execute(total_q)
    result = await session.execute(q)
    logs = result.scalars().all()

    entries = []
    for l in logs:
        ch_name = None
        key_value = None
        if l.channel_id:
            ch = await session.get(Channel, l.channel_id)
            ch_name = ch.name if ch else None
        if l.key_id:
            k = await session.get(Key, l.key_id)
            key_value = k.value[:20] + "..." if k else None
        entries.append({
            "id": l.id,
            "timestamp": str(l.timestamp) if l.timestamp else None,
            "channel": ch_name,
            "channel_id": l.channel_id,
            "key": key_value,
            "key_id": l.key_id,
            "model": l.model,
            "prompt_tokens": l.prompt_tokens,
            "completion_tokens": l.completion_tokens,
            "response_time": l.response_time,
            "status_code": l.status_code,
            "error_message": l.error_message,
            "is_streaming": l.is_streaming,
        })

    return {"total": total.scalar() or 0, "entries": entries}


@router.get("/config")
async def get_config():
    return {
        "host": HOST,
        "port": PORT,
        "health_check_interval": HEALTH_CHECK_INTERVAL,
        "health_check_timeout": 10,
        "health_check_max_errors": HEALTH_CHECK_MAX_ERRORS,
        "max_retry_count": MAX_RETRY_COUNT,
        "proxy_url": PROXY_URL,
    }


@router.put("/config")
async def update_config():
    # Config is loaded from env vars; return current values
    # In a production app, we'd persist these to DB
    return {"message": "Configuration is managed via environment variables. See README for details."}