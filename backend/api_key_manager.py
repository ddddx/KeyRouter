import secrets
import time
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from database import get_session
from models import ApiKey, Channel

logger = logging.getLogger("api_key_manager")

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])

DEFAULT_PREFIX = "sk-keyrouter-"


class ApiKeyCreate(BaseModel):
    name: Optional[str] = None
    channel_id: Optional[int] = None
    enabled: bool = True
    rate_limit: Optional[int] = None
    total_quota: Optional[float] = None
    expires_at: Optional[str] = None  # ISO datetime string
    prefix: Optional[str] = None  # custom prefix, defaults to sk-keyrouter-
    custom_value: Optional[str] = None  # if set, use this exact value instead of auto-generating


class ApiKeyBatchCreate(BaseModel):
    count: int = 1  # number of keys to generate (1-100)
    name_prefix: Optional[str] = None  # e.g. "test-", generates "test-1", "test-2", ...
    channel_id: Optional[int] = None
    enabled: bool = True
    rate_limit: Optional[int] = None
    total_quota: Optional[float] = None
    expires_at: Optional[str] = None
    prefix: Optional[str] = None


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    channel_id: Optional[int] = None
    enabled: Optional[bool] = None
    rate_limit: Optional[int] = None
    total_quota: Optional[float] = None
    expires_at: Optional[str] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: Optional[str] = None
    value: str
    value_masked: str
    channel_id: Optional[int] = None
    channel_name: Optional[str] = None
    enabled: bool
    rate_limit: Optional[int] = None
    total_quota: Optional[float] = None
    used_quota: float
    total_requests: int
    quota_remaining: Optional[float] = None
    status: str  # active / disabled / expired / exhausted
    created_at: Optional[str] = None
    expires_at: Optional[str] = None

    class Config:
        from_attributes = True


def _generate_key_value(prefix: str = DEFAULT_PREFIX) -> str:
    """Generate a random API key value with the given prefix."""
    random_part = secrets.token_urlsafe(24).replace("-", "").replace("_", "")[:24]
    return prefix + random_part


def mask_api_key(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return val
    return val[:8] + "***"


def _compute_status(api_key: ApiKey) -> str:
    """Determine the display status of an ApiKey."""
    if not api_key.enabled:
        return "disabled"
    if api_key.expires_at and api_key.expires_at < datetime.now():
        return "expired"
    if api_key.total_quota is not None and api_key.used_quota >= api_key.total_quota:
        return "exhausted"
    return "active"


def make_api_key_response(ak: ApiKey, ch_name: str = None) -> ApiKeyResponse:
    quota_remaining = None
    if ak.total_quota is not None:
        quota_remaining = max(0, ak.total_quota - ak.used_quota)
    return ApiKeyResponse(
        id=ak.id,
        name=ak.name,
        value=ak.value,
        value_masked=mask_api_key(ak.value),
        channel_id=ak.channel_id,
        channel_name=ch_name,
        enabled=ak.enabled,
        rate_limit=ak.rate_limit,
        total_quota=ak.total_quota,
        used_quota=round(ak.used_quota, 4),
        total_requests=ak.total_requests,
        quota_remaining=round(quota_remaining, 4) if quota_remaining is not None else None,
        status=_compute_status(ak),
        created_at=str(ak.created_at) if ak.created_at else None,
        expires_at=str(ak.expires_at) if ak.expires_at else None,
    )


# ─── CRUD ───

@router.get("", response_model=list[ApiKeyResponse], include_in_schema=False)
@router.get("/", response_model=list[ApiKeyResponse])
async def list_api_keys(
    channel_id: Optional[int] = None,
    enabled: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(ApiKey).order_by(ApiKey.id)
    if channel_id is not None:
        q = q.where(ApiKey.channel_id == channel_id)
    if enabled is not None:
        q = q.where(ApiKey.enabled == enabled)
    result = await session.execute(q)
    keys = result.scalars().all()

    # Cache channel names
    channels_cache = {}
    for ak in keys:
        if ak.channel_id and ak.channel_id not in channels_cache:
            ch = await session.get(Channel, ak.channel_id)
            channels_cache[ak.channel_id] = ch
        elif ak.channel_id is None and None not in channels_cache:
            channels_cache[None] = None

    responses = []
    for ak in keys:
        ch = channels_cache.get(ak.channel_id)
        ch_name = ch.name if ch else None
        responses.append(make_api_key_response(ak, ch_name))
    return responses


@router.post("", response_model=ApiKeyResponse, include_in_schema=False)
@router.post("/", response_model=ApiKeyResponse)
async def create_api_key(data: ApiKeyCreate, session: AsyncSession = Depends(get_session)):
    # Validate channel if specified
    if data.channel_id is not None:
        ch = await session.get(Channel, data.channel_id)
        if not ch:
            raise HTTPException(404, "Channel not found")

    # Use custom value or auto-generate
    value = data.custom_value or _generate_key_value(data.prefix or DEFAULT_PREFIX)

    # Check uniqueness
    existing = await session.execute(select(ApiKey).where(ApiKey.value == value))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Key value already exists")

    expires_at = None
    if data.expires_at:
        try:
            expires_at = datetime.fromisoformat(data.expires_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "Invalid expires_at format, use ISO datetime")

    ak = ApiKey(
        name=data.name,
        value=value,
        channel_id=data.channel_id,
        enabled=data.enabled,
        rate_limit=data.rate_limit,
        total_quota=data.total_quota,
        used_quota=0.0,
        total_requests=0,
        expires_at=expires_at,
    )
    session.add(ak)
    await session.commit()
    await session.refresh(ak)

    ch_name = None
    if ak.channel_id:
        ch = await session.get(Channel, ak.channel_id)
        ch_name = ch.name if ch else None
    return make_api_key_response(ak, ch_name)


@router.post("/batch", response_model=list[ApiKeyResponse])
async def batch_create_api_keys(data: ApiKeyBatchCreate, session: AsyncSession = Depends(get_session)):
    if data.count < 1 or data.count > 100:
        raise HTTPException(400, "Count must be between 1 and 100")

    # Validate channel if specified
    ch_name = None
    if data.channel_id is not None:
        ch = await session.get(Channel, data.channel_id)
        if not ch:
            raise HTTPException(404, "Channel not found")
        ch_name = ch.name

    prefix = data.prefix or DEFAULT_PREFIX
    expires_at = None
    if data.expires_at:
        try:
            expires_at = datetime.fromisoformat(data.expires_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "Invalid expires_at format, use ISO datetime")

    created = []
    for i in range(data.count):
        value = _generate_key_value(prefix)
        name = f"{data.name_prefix or ''}{i + 1}" if data.name_prefix else None
        ak = ApiKey(
            name=name,
            value=value,
            channel_id=data.channel_id,
            enabled=data.enabled,
            rate_limit=data.rate_limit,
            total_quota=data.total_quota,
            used_quota=0.0,
            total_requests=0,
            expires_at=expires_at,
        )
        session.add(ak)
        created.append(ak)

    await session.commit()
    responses = []
    for ak in created:
        await session.refresh(ak)
        responses.append(make_api_key_response(ak, ch_name))
    return responses


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(key_id: int, data: ApiKeyUpdate, session: AsyncSession = Depends(get_session)):
    ak = await session.get(ApiKey, key_id)
    if not ak:
        raise HTTPException(404, "Api key not found")

    # Validate channel if being changed
    if data.channel_id is not None:
        ch = await session.get(Channel, data.channel_id)
        if not ch:
            raise HTTPException(404, "Channel not found")

    expires_at = ak.expires_at
    if data.expires_at is not None:
        try:
            expires_at = datetime.fromisoformat(data.expires_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "Invalid expires_at format")
        ak.expires_at = expires_at

    update_data = data.model_dump(exclude_unset=True)
    # Handle expires_at separately since we already processed it
    if "expires_at" in update_data:
        del update_data["expires_at"]
    for attr, val in update_data.items():
        setattr(ak, attr, val)

    await session.commit()
    await session.refresh(ak)

    ch_name = None
    if ak.channel_id:
        ch = await session.get(Channel, ak.channel_id)
        ch_name = ch.name if ch else None
    return make_api_key_response(ak, ch_name)


@router.delete("/{key_id}")
async def delete_api_key(key_id: int, session: AsyncSession = Depends(get_session)):
    ak = await session.get(ApiKey, key_id)
    if not ak:
        raise HTTPException(404, "Api key not found")
    await session.delete(ak)
    await session.commit()
    return {"message": "Api key deleted"}


# ─── Validation helpers (used by router) ───

async def validate_api_key(
    api_key_value: str,
    session: AsyncSession,
) -> ApiKey:
    """Validate an incoming external API key. Returns the ApiKey object or raises HTTPException."""
    result = await session.execute(select(ApiKey).where(ApiKey.value == api_key_value))
    ak = result.scalar_one_or_none()

    if ak is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not ak.enabled:
        raise HTTPException(status_code=403, detail="API key is disabled")

    if ak.expires_at and ak.expires_at < datetime.now():
        raise HTTPException(status_code=403, detail="API key has expired")

    if ak.total_quota is not None and ak.used_quota >= ak.total_quota:
        raise HTTPException(status_code=403, detail="API key quota exhausted")

    # Rate limit check (per-minute sliding window)
    if ak.rate_limit is not None:
        # Simple approach: use total_requests in last 60s via request_logs
        # For efficiency, we use a lightweight in-memory counter approach
        now_ts = time.time()
        counter_key = ak.id
        if counter_key in _rate_limit_counters:
            window_start, count = _rate_limit_counters[counter_key]
            if now_ts - window_start > 60:
                # Reset window
                _rate_limit_counters[counter_key] = (now_ts, 1)
            else:
                if count >= ak.rate_limit:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                _rate_limit_counters[counter_key] = (window_start, count + 1)
        else:
            _rate_limit_counters[counter_key] = (now_ts, 1)

    return ak


async def update_api_key_usage(
    ak: ApiKey,
    prompt_tokens: int,
    completion_tokens: int,
    session: AsyncSession,
):
    """Update usage stats for an external ApiKey after a successful request."""
    from models import QUOTA_PRICING_COEFFICIENT
    total_tokens = prompt_tokens + completion_tokens
    ak.used_quota += total_tokens * QUOTA_PRICING_COEFFICIENT
    ak.total_requests += 1
    await session.commit()


# In-memory rate limit counter: api_key_id -> (window_start_timestamp, request_count)
_rate_limit_counters: dict[int, tuple[float, int]] = {}
