import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case, extract
from typing import Optional
from datetime import datetime, timedelta
from database import get_session
from models import Channel, Key, RequestLog, ApiKey
from config import HEALTH_CHECK_INTERVAL, HEALTH_CHECK_MAX_ERRORS, MAX_RETRY_COUNT, PORT, HOST, PROXY_URL, LOG_RETENTION_DAYS

router = APIRouter(prefix="/api/admin", tags=["admin"])


def mask_key(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return val
    return val[:8] + "***"


def fmt_time(ts) -> str:
    if not ts:
        return "-"
    s = str(ts)
    return s.replace("T", " ").substring(0, 19) if "T" in s else s[:19]


# ─── Dashboard Stats ───

@router.get("/stats/dashboard")
async def dashboard_stats(session: AsyncSession = Depends(get_session)):
    # Basic counts
    total_requests = await session.execute(select(func.count(RequestLog.id)))
    success_requests = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.is_success == True)
    )
    failed_requests = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.is_success == False)
    )
    total_channels = await session.execute(select(func.count(Channel.id)))
    active_channels = await session.execute(select(func.count(Channel.id)).where(Channel.enabled == True))
    total_keys = await session.execute(select(func.count(Key.id)))
    active_keys = await session.execute(select(func.count(Key.id)).where(Key.status == "active"))
    error_keys = await session.execute(select(func.count(Key.id)).where(Key.status == "error"))

    avg_response_ms = await session.execute(
        select(func.avg(RequestLog.response_time_ms)).where(RequestLog.is_success == True)
    )
    total_prompt_tokens = await session.execute(select(func.sum(RequestLog.prompt_tokens)))
    total_completion_tokens = await session.execute(select(func.sum(RequestLog.completion_tokens)))
    # Fetch scalar values immediately to avoid ResourceClosedError
    tr_val = total_requests.scalar() or 0
    sr_val = success_requests.scalar() or 0
    fr_val = failed_requests.scalar() or 0
    tc_val = total_channels.scalar() or 0
    ac_val = active_channels.scalar() or 0
    tk_val = total_keys.scalar() or 0
    ak_val = active_keys.scalar() or 0
    ek_val = error_keys.scalar() or 0
    avg_rt_val = round(avg_response_ms.scalar() or 0, 3)
    tp_val = total_prompt_tokens.scalar() or 0
    tc2_val = total_completion_tokens.scalar() or 0
    total_tokens_val = tp_val + tc2_val

    success_rate = round(sr_val / tr_val * 100, 2) if tr_val > 0 else 0
    error_rate = round(fr_val / tr_val * 100, 2) if tr_val > 0 else 0

    # Recent errors (last 10)
    recent_errors_result = await session.execute(
        select(RequestLog).where(RequestLog.is_success == False).order_by(desc(RequestLog.id)).limit(10)
    )
    recent_errors = []
    for e in recent_errors_result.scalars().all():
        ch_name = None
        key_masked = None
        if e.channel_id:
            ch = await session.get(Channel, e.channel_id)
            ch_name = ch.name if ch else None
        if e.key_id:
            k = await session.get(Key, e.key_id)
            key_masked = mask_key(k.value) if k else None
        recent_errors.append({
            "timestamp": str(e.timestamp) if e.timestamp else None,
            "channel": ch_name,
            "key": key_masked,
            "model": e.model,
            "status_code": e.status_code,
            "source_ip": e.source_ip,
            "error_message": e.error_message,
        })

    # Model usage stats
    model_stats_result = await session.execute(
        select(
            RequestLog.model,
            func.count(RequestLog.id).label("total_requests"),
            func.sum(case((RequestLog.is_success == True, 1), else_=0)).label("success_requests"),
            func.avg(RequestLog.response_time_ms).label("avg_response_time_ms"),
            func.sum(RequestLog.prompt_tokens).label("total_prompt_tokens"),
            func.sum(RequestLog.completion_tokens).label("total_completion_tokens"),
        )
        .where(RequestLog.model != None)
        .group_by(RequestLog.model)
        .order_by(desc(func.count(RequestLog.id)))
    )
    model_stats = []
    for row in model_stats_result.all():
        mr = row.total_requests or 0
        ms = row.success_requests or 0
        model_stats.append({
            "model": row.model,
            "total_requests": mr,
            "success_requests": ms,
            "failed_requests": mr - ms,
            "success_rate": round(ms / mr * 100, 2) if mr > 0 else 0,
            "avg_response_time_ms": round(row.avg_response_time_ms or 0, 1),
            "total_tokens": (row.total_prompt_tokens or 0) + (row.total_completion_tokens or 0),
        })

    # Hourly trend (last 48 hours)
    hourly_trend = await _get_hourly_trend(session, hours=48)

    # Daily trend (last 30 days)
    daily_trend = await _get_daily_trend(session, days=30)

    # ApiKey stats
    total_api_keys = await session.execute(select(func.count(ApiKey.id)))
    active_api_keys = await session.execute(select(func.count(ApiKey.id)).where(ApiKey.enabled == True))
    tak_val = total_api_keys.scalar() or 0
    aak_val = active_api_keys.scalar() or 0

    return {
        "total_requests": tr_val,
        "success_requests": sr_val,
        "failed_requests": fr_val,
        "success_rate": success_rate,
        "error_rate": error_rate,
        "total_channels": tc_val,
        "active_channels": ac_val,
        "total_keys": tk_val,
        "active_keys": ak_val,
        "error_keys": ek_val,
        "total_api_keys": tak_val,
        "active_api_keys": aak_val,
        "avg_response_time_ms": avg_rt_val,
        "total_tokens": total_tokens_val,
        "total_prompt_tokens": tp_val,
        "total_completion_tokens": tc2_val,
        "recent_errors": recent_errors,
        "model_stats": model_stats,
        "hourly_trend": hourly_trend,
        "daily_trend": daily_trend,
    }


async def _get_hourly_trend(session: AsyncSession, hours: int = 48):
    """Get request counts grouped by hour for the last N hours."""
    cutoff = datetime.now() - timedelta(hours=hours)
    result = await session.execute(
        select(
            func.strftime("%Y-%m-%d %H:00", RequestLog.timestamp).label("hour"),
            func.count(RequestLog.id).label("total"),
            func.sum(case((RequestLog.is_success == True, 1), else_=0)).label("success"),
            func.sum(case((RequestLog.is_success == False, 1), else_=0)).label("failed"),
        )
        .where(RequestLog.timestamp >= cutoff)
        .group_by(func.strftime("%Y-%m-%d %H:00", RequestLog.timestamp))
        .order_by(func.strftime("%Y-%m-%d %H:00", RequestLog.timestamp))
    )
    return [
        {
            "time": row.hour,
            "total": row.total,
            "success": row.success or 0,
            "failed": row.failed or 0,
        }
        for row in result.all()
    ]


async def _get_daily_trend(session: AsyncSession, days: int = 30):
    """Get request counts grouped by day for the last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(
            func.strftime("%Y-%m-%d", RequestLog.timestamp).label("day"),
            func.count(RequestLog.id).label("total"),
            func.sum(case((RequestLog.is_success == True, 1), else_=0)).label("success"),
            func.sum(case((RequestLog.is_success == False, 1), else_=0)).label("failed"),
        )
        .where(RequestLog.timestamp >= cutoff)
        .group_by(func.strftime("%Y-%m-%d", RequestLog.timestamp))
        .order_by(func.strftime("%Y-%m-%d", RequestLog.timestamp))
    )
    return [
        {
            "time": row.day,
            "total": row.total,
            "success": row.success or 0,
            "failed": row.failed or 0,
        }
        for row in result.all()
    ]


# ─── Channel Stats ───

@router.get("/stats/channel/{channel_id}")
async def channel_stats(channel_id: int, session: AsyncSession = Depends(get_session)):
    ch = await session.get(Channel, channel_id)
    if not ch:
        return {"error": "Channel not found"}

    tr_result = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.channel_id == channel_id)
    )
    sr_result = await session.execute(
        select(func.count(RequestLog.id)).where(
            RequestLog.channel_id == channel_id, RequestLog.is_success == True
        )
    )
    fr_result = await session.execute(
        select(func.count(RequestLog.id)).where(
            RequestLog.channel_id == channel_id, RequestLog.is_success == False
        )
    )
    avg_rt = await session.execute(
        select(func.avg(RequestLog.response_time_ms)).where(
            RequestLog.channel_id == channel_id, RequestLog.is_success == True
        )
    )
    total_pt = await session.execute(
        select(func.sum(RequestLog.prompt_tokens)).where(RequestLog.channel_id == channel_id)
    )
    total_ct = await session.execute(
        select(func.sum(RequestLog.completion_tokens)).where(RequestLog.channel_id == channel_id)
    )
    key_count = await session.execute(select(func.count(Key.id)).where(Key.channel_id == channel_id))
    active_key_count = await session.execute(
        select(func.count(Key.id)).where(Key.channel_id == channel_id, Key.status == "active")
    )
    error_key_count = await session.execute(
        select(func.count(Key.id)).where(Key.channel_id == channel_id, Key.status == "error")
    )

    tr = tr_result.scalar() or 0
    sr = sr_result.scalar() or 0
    fr = fr_result.scalar() or 0

    # Per-key stats for this channel
    keys_result = await session.execute(
        select(Key).where(Key.channel_id == channel_id).order_by(Key.id)
    )
    key_stats = []
    for k in keys_result.scalars().all():
        k_tr_result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.key_id == k.id)
        )
        k_sr_result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.key_id == k.id, RequestLog.is_success == True)
        )
        k_avg_rt = await session.execute(
            select(func.avg(RequestLog.response_time_ms)).where(RequestLog.key_id == k.id, RequestLog.is_success == True)
        )
        k_tr = k_tr_result.scalar() or 0
        k_sr = k_sr_result.scalar() or 0
        key_stats.append({
            "key_id": k.id,
            "key_masked": mask_key(k.value),
            "status": k.status,
            "total_requests": k.total_requests,
            "success_requests": k.success_requests,
            "failed_requests": k.failed_requests,
            "success_rate": round(k.success_requests / k.total_requests * 100, 2) if k.total_requests > 0 else 0,
            "avg_response_time_ms": round(k.avg_response_time, 1),
            "total_tokens": k.total_prompt_tokens + k.total_completion_tokens,
            "last_used": str(k.last_used) if k.last_used else None,
        })

    # Daily trend for channel
    cutoff = datetime.now() - timedelta(days=30)
    trend_result = await session.execute(
        select(
            func.strftime("%Y-%m-%d", RequestLog.timestamp).label("day"),
            func.count(RequestLog.id).label("total"),
            func.sum(case((RequestLog.is_success == True, 1), else_=0)).label("success"),
        )
        .where(RequestLog.channel_id == channel_id, RequestLog.timestamp >= cutoff)
        .group_by(func.strftime("%Y-%m-%d", RequestLog.timestamp))
        .order_by(func.strftime("%Y-%m-%d", RequestLog.timestamp))
    )
    daily_trend = [
        {"time": row.day, "total": row.total, "success": row.success or 0}
        for row in trend_result.all()
    ]

    return {
        "channel_id": channel_id,
        "channel_name": ch.name,
        "total_requests": tr,
        "success_requests": sr,
        "failed_requests": fr,
        "success_rate": round(sr / tr * 100, 2) if tr > 0 else 0,
        "avg_response_time_ms": round(avg_rt.scalar() or 0, 1),
        "total_tokens": (total_pt.scalar() or 0) + (total_ct.scalar() or 0),
        "key_count": key_count.scalar() or 0,
        "active_key_count": active_key_count.scalar() or 0,
        "error_key_count": error_key_count.scalar() or 0,
        "key_stats": key_stats,
        "daily_trend": daily_trend,
    }


# ─── Key Stats ───

@router.get("/stats/key/{key_id}")
async def key_stats(key_id: int, session: AsyncSession = Depends(get_session)):
    k = await session.get(Key, key_id)
    if not k:
        return {"error": "Key not found"}

    return {
        "key_id": key_id,
        "key_masked": mask_key(k.value),
        "channel_id": k.channel_id,
        "status": k.status,
        "total_requests": k.total_requests,
        "success_requests": k.success_requests,
        "failed_requests": k.failed_requests,
        "success_rate": round(k.success_requests / k.total_requests * 100, 2) if k.total_requests > 0 else 0,
        "avg_response_time_ms": round(k.avg_response_time, 1),
        "error_count": k.error_count,
        "total_tokens": k.total_prompt_tokens + k.total_completion_tokens,
        "total_prompt_tokens": k.total_prompt_tokens,
        "total_completion_tokens": k.total_completion_tokens,
        "last_used": str(k.last_used) if k.last_used else None,
    }


# ─── Logs ───

@router.get("/logs")
async def get_logs(
    channel_id: Optional[int] = None,
    key_id: Optional[int] = None,
    model: Optional[str] = None,
    status_code: Optional[int] = None,
    is_success: Optional[bool] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    session: AsyncSession = Depends(get_session),
):
    q = select(RequestLog).order_by(desc(RequestLog.id))
    total_q = select(func.count(RequestLog.id))

    if channel_id:
        q = q.where(RequestLog.channel_id == channel_id)
        total_q = total_q.where(RequestLog.channel_id == channel_id)
    if key_id:
        q = q.where(RequestLog.key_id == key_id)
        total_q = total_q.where(RequestLog.key_id == key_id)
    if model:
        q = q.where(RequestLog.model == model)
        total_q = total_q.where(RequestLog.model == model)
    if status_code:
        q = q.where(RequestLog.status_code == status_code)
        total_q = total_q.where(RequestLog.status_code == status_code)
    if is_success is not None:
        q = q.where(RequestLog.is_success == is_success)
        total_q = total_q.where(RequestLog.is_success == is_success)
    if start_time:
        q = q.where(RequestLog.timestamp >= start_time)
        total_q = total_q.where(RequestLog.timestamp >= start_time)
    if end_time:
        q = q.where(RequestLog.timestamp <= end_time)
        total_q = total_q.where(RequestLog.timestamp <= end_time)

    q = q.offset(offset).limit(limit)

    total = await session.execute(total_q)
    result = await session.execute(q)
    logs = result.scalars().all()

    # Pre-load channels and keys to avoid N+1
    channels_cache = {}
    keys_cache = {}
    for l in logs:
        if l.channel_id and l.channel_id not in channels_cache:
            ch = await session.get(Channel, l.channel_id)
            channels_cache[l.channel_id] = ch
        if l.key_id and l.key_id not in keys_cache:
            k = await session.get(Key, l.key_id)
            keys_cache[l.key_id] = k

    entries = []
    for l in logs:
        ch_name = channels_cache.get(l.channel_id)
        ch_name = ch_name.name if ch_name else None
        k_obj = keys_cache.get(l.key_id)
        key_masked = mask_key(k_obj.value) if k_obj else None

        entries.append({
            "id": l.id,
            "timestamp": str(l.timestamp) if l.timestamp else None,
            "channel": ch_name,
            "channel_id": l.channel_id,
            "key": key_masked,
            "key_id": l.key_id,
            "model": l.model,
            "prompt_tokens": l.prompt_tokens or 0,
            "completion_tokens": l.completion_tokens or 0,
            "total_tokens": (l.prompt_tokens or 0) + (l.completion_tokens or 0),
            "response_time_ms": l.response_time_ms or 0,
            "status_code": l.status_code,
            "is_success": l.is_success,
            "error_message": l.error_message,
            "is_streaming": l.is_streaming,
            "source_ip": l.source_ip,
        })

    return {"total": total.scalar() or 0, "entries": entries}


# ─── CSV Export ───

@router.get("/logs/export/csv")
async def export_logs_csv(
    channel_id: Optional[int] = None,
    key_id: Optional[int] = None,
    model: Optional[str] = None,
    status_code: Optional[int] = None,
    is_success: Optional[bool] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(RequestLog).order_by(desc(RequestLog.id)).limit(5000)

    if channel_id:
        q = q.where(RequestLog.channel_id == channel_id)
    if key_id:
        q = q.where(RequestLog.key_id == key_id)
    if model:
        q = q.where(RequestLog.model == model)
    if status_code:
        q = q.where(RequestLog.status_code == status_code)
    if is_success is not None:
        q = q.where(RequestLog.is_success == is_success)
    if start_time:
        q = q.where(RequestLog.timestamp >= start_time)
    if end_time:
        q = q.where(RequestLog.timestamp <= end_time)

    result = await session.execute(q)
    logs = result.scalars().all()

    # Pre-load
    channels_cache = {}
    keys_cache = {}
    for l in logs:
        if l.channel_id and l.channel_id not in channels_cache:
            ch = await session.get(Channel, l.channel_id)
            channels_cache[l.channel_id] = ch
        if l.key_id and l.key_id not in keys_cache:
            k = await session.get(Key, l.key_id)
            keys_cache[l.key_id] = k

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp", "channel", "key_masked", "model",
        "prompt_tokens", "completion_tokens", "total_tokens",
        "response_time_ms", "status_code", "is_success",
        "error_message", "is_streaming", "source_ip",
    ])

    for l in logs:
        ch_name = None
        if l.channel_id:
            ch = channels_cache.get(l.channel_id)
            ch_name = ch.name if ch else None
        key_masked = None
        if l.key_id:
            k = keys_cache.get(l.key_id)
            key_masked = mask_key(k.value) if k else None

        writer.writerow([
            str(l.timestamp) if l.timestamp else "",
            ch_name or "",
            key_masked or "",
            l.model or "",
            l.prompt_tokens or 0,
            l.completion_tokens or 0,
            (l.prompt_tokens or 0) + (l.completion_tokens or 0),
            l.response_time_ms or 0,
            l.status_code or 0,
            l.is_success,
            l.error_message or "",
            l.is_streaming,
            l.source_ip or "",
        ])

    output.seek(0)
    filename = f"keyrouter_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Config ───

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
        "log_retention_days": LOG_RETENTION_DAYS,
    }


@router.put("/config")
async def update_config():
    return {"message": "Configuration is managed via environment variables. See README for details."}