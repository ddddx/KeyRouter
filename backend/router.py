import time
import json
import logging
from datetime import datetime
from typing import Optional, AsyncIterator
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_session, get_db_session
from models import Key, Channel, RequestLog, ApiKey
from key_manager import select_key
from api_key_manager import validate_api_key, update_api_key_usage
from config import MAX_RETRY_COUNT, ROUTING_TIMEOUT, PROXY_URL
import httpx

logger = logging.getLogger("router")

router = APIRouter(tags=["proxy"])


def mask_key_value(val: str) -> str:
    """Mask key: show first 8 chars + ***."""
    if not val:
        return ""
    if len(val) <= 8:
        return val
    return val[:8] + "***"


def extract_source_ip(request: Request) -> str:
    """Extract client IP from request headers."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


async def stream_forward(
    channel: Channel,
    key: Key,
    path: str,
    body: dict,
    source_ip: str,
    session: AsyncSession,
):
    """Forward streaming request and yield chunks in real-time."""
    url = channel.base_url.rstrip("/") + path
    headers = {
        "Authorization": f"Bearer {key.value}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    proxy = PROXY_URL if PROXY_URL else None
    start_time = time.time()
    model = body.get("model", None)
    status_code = 200
    prompt_tokens = 0
    completion_tokens = 0

    async with httpx.AsyncClient(timeout=ROUTING_TIMEOUT, proxy=proxy) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            status_code = resp.status_code

            if status_code >= 400:
                error_body = await resp.aread()
                elapsed_ms = int((time.time() - start_time) * 1000)
                await update_key_stats(session, key, False, elapsed_ms)
                try:
                    error_data = json.loads(error_body)
                    error_msg = error_data.get("error", {}).get("message", str(error_body[:200]))
                except Exception:
                    error_msg = error_body.decode()[:200]
                await log_request(session, channel.id, key.id, model, 0, 0, elapsed_ms, status_code, False, error_msg, True, source_ip)
                return None, error_body, status_code, 0, 0

            # Collect chunks while streaming to client
            chunks_collected = []

            async for chunk in resp.aiter_bytes():
                chunks_collected.append(chunk)
                # Parse SSE data for token usage
                try:
                    text = chunk.decode()
                    for line in text.split("\n"):
                        if line.startswith("data: ") and line != "data: [DONE]":
                            data_str = line[6:]
                            try:
                                d = json.loads(data_str)
                                usage = d.get("usage", {})
                                if usage:
                                    prompt_tokens = usage.get("prompt_tokens", 0)
                                    completion_tokens = usage.get("completion_tokens", 0)
                            except json.JSONDecodeError:
                                pass
                except Exception:
                    pass

            elapsed_ms = int((time.time() - start_time) * 1000)

            async def generate():
                for c in chunks_collected:
                    yield c

            await update_key_stats(session, key, True, elapsed_ms, prompt_tokens, completion_tokens)
            await log_request(session, channel.id, key.id, model, prompt_tokens, completion_tokens, elapsed_ms, status_code, True, None, True, source_ip)

            return generate(), None, status_code, prompt_tokens, completion_tokens


async def non_stream_forward(
    channel: Channel,
    key: Key,
    path: str,
    body: dict,
    source_ip: str,
    session: AsyncSession,
):
    """Forward non-streaming request."""
    url = channel.base_url.rstrip("/") + path
    headers = {
        "Authorization": f"Bearer {key.value}",
        "Content-Type": "application/json",
    }
    proxy = PROXY_URL if PROXY_URL else None
    start_time = time.time()
    model = body.get("model", None)

    async with httpx.AsyncClient(timeout=ROUTING_TIMEOUT, proxy=proxy) as client:
        resp = await client.post(url, json=body, headers=headers)
        elapsed_ms = int((time.time() - start_time) * 1000)
        status_code = resp.status_code
        success = status_code < 400

        prompt_tokens = 0
        completion_tokens = 0
        error_msg = None

        try:
            resp_data = resp.json()
            usage = resp_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            if "error" in resp_data:
                error_msg = resp_data["error"].get("message", str(resp_data["error"]))
        except Exception:
            error_msg = resp.text[:500] if status_code >= 400 else None

        await update_key_stats(session, key, success, elapsed_ms, prompt_tokens, completion_tokens)
        await log_request(session, channel.id, key.id, model, prompt_tokens, completion_tokens, elapsed_ms, status_code, success, error_msg, False, source_ip)

        return resp, elapsed_ms, status_code


async def log_request(
    session: AsyncSession,
    channel_id: int,
    key_id: int,
    model: Optional[str],
    prompt_tokens: int,
    completion_tokens: int,
    response_time_ms: int,
    status_code: int,
    is_success: bool,
    error_message: Optional[str],
    is_streaming: bool,
    source_ip: str,
):
    log = RequestLog(
        channel_id=channel_id,
        key_id=key_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        response_time_ms=response_time_ms,
        status_code=status_code,
        is_success=is_success,
        error_message=error_message,
        is_streaming=is_streaming,
        source_ip=source_ip,
    )
    session.add(log)
    await session.commit()


async def update_key_stats(
    session: AsyncSession,
    key: Key,
    success: bool,
    response_time_ms: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
):
    key.last_used = datetime.now()
    key.total_requests += 1
    if success:
        key.success_requests += 1
        # Running average of response time in ms
        if key.avg_response_time == 0:
            key.avg_response_time = response_time_ms
        else:
            key.avg_response_time = (key.avg_response_time * (key.success_requests - 1) + response_time_ms) / key.success_requests
        key.total_prompt_tokens += prompt_tokens
        key.total_completion_tokens += completion_tokens
    else:
        key.failed_requests += 1
        key.error_count += 1
    await session.commit()


def extract_api_key_from_request(request: Request) -> Optional[str]:
    """Extract the external API key from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


async def proxy_request(request: Request, path: str, body: dict):
    """Core proxy logic with retry and key selection."""
    is_stream = body.get("stream", False)
    model = body.get("model", None)
    source_ip = extract_source_ip(request)
    attempted_keys = []

    # ─── Validate external API key ───
    api_key_value = extract_api_key_from_request(request)
    if not api_key_value:
        raise HTTPException(status_code=401, detail="Authorization required. Provide a valid API key via Authorization: Bearer sk-keyrouter-xxx")

    api_key_obj: ApiKey = None
    bound_channel_id: Optional[int] = None

    async with get_db_session() as auth_session:
        api_key_obj = await validate_api_key(api_key_value, auth_session)
        bound_channel_id = api_key_obj.channel_id  # None means auto-match by model

    for attempt in range(MAX_RETRY_COUNT):
        async with get_db_session() as session:
            # Determine which channels to use
            if bound_channel_id is not None:
                # ApiKey is bound to a specific channel
                channel = await session.get(Channel, bound_channel_id)
                if not channel or not channel.enabled:
                    raise HTTPException(503, "Bound channel is not available")
                channels = [channel]
            else:
                # Auto-match: find enabled channels (existing logic)
                channels_result = await session.execute(
                    select(Channel).where(Channel.enabled == True)
                )
                channels = channels_result.scalars().all()

            if not channels:
                raise HTTPException(503, "No enabled channels available")

            for channel in channels:
                key = await select_key(channel.id, channel.strategy, session)
                if not key:
                    continue
                if key.id in attempted_keys:
                    continue

                attempted_keys.append(key.id)

                try:
                    if is_stream:
                        result = await stream_forward(channel, key, path, body, source_ip, session)

                        generator, error_body, status_code, s_prompt_tokens, s_completion_tokens = result
                        if generator is None:
                            if status_code == 429:
                                logger.warning(f"Key {key.id} rate limited (stream), retrying...")
                                continue
                            elif status_code == 401:
                                async with get_db_session() as s:
                                    k = await s.get(Key, key.id)
                                    if k:
                                        k.status = "error"
                                        k.error_count += 3
                                        await s.commit()
                                continue
                            elif status_code >= 500:
                                logger.warning(f"Key {key.id} got {status_code} (stream), retrying...")
                                continue
                            else:
                                try:
                                    err_json = json.loads(error_body)
                                except Exception:
                                    err_json = {"error": {"message": error_body.decode()[:200]}}
                                return JSONResponse(content=err_json, status_code=status_code)

                        # Update ApiKey usage after successful stream
                        async with get_db_session() as usage_session:
                            ak_obj = await usage_session.get(ApiKey, api_key_obj.id)
                            if ak_obj:
                                await update_api_key_usage(ak_obj, s_prompt_tokens, s_completion_tokens, usage_session)

                        return StreamingResponse(
                            generator(),
                            media_type="text/event-stream",
                            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                        )
                    else:
                        resp, elapsed_ms, status_code = await non_stream_forward(channel, key, path, body, source_ip, session)

                        # Extract tokens from response for ApiKey tracking
                        _ns_prompt_tokens = 0
                        _ns_completion_tokens = 0
                        if status_code < 400:
                            try:
                                resp_data = resp.json()
                                usage_info = resp_data.get("usage", {})
                                _ns_prompt_tokens = usage_info.get("prompt_tokens", 0)
                                _ns_completion_tokens = usage_info.get("completion_tokens", 0)
                            except Exception:
                                pass

                        if status_code < 400:
                            # Update ApiKey usage after successful non-stream request
                            async with get_db_session() as usage_session:
                                ak_obj = await usage_session.get(ApiKey, api_key_obj.id)
                                if ak_obj:
                                    await update_api_key_usage(ak_obj, _ns_prompt_tokens, _ns_completion_tokens, usage_session)
                            return JSONResponse(content=resp.json(), status_code=status_code)
                        elif status_code == 429:
                            logger.warning(f"Key {key.id} rate limited, retrying...")
                            continue
                        elif status_code >= 500:
                            logger.warning(f"Key {key.id} got {status_code}, retrying...")
                            continue
                        elif status_code == 401:
                            async with get_db_session() as s:
                                k = await s.get(Key, key.id)
                                if k:
                                    k.status = "error"
                                    k.error_count += 3
                                    await s.commit()
                            continue
                        else:
                            return JSONResponse(content=resp.json(), status_code=status_code)

                except httpx.TimeoutException:
                    logger.warning(f"Key {key.id} timeout, retrying...")
                    timeout_ms = ROUTING_TIMEOUT * 1000
                    async with get_db_session() as s:
                        k = await s.get(Key, key.id)
                        if k:
                            await update_key_stats(s, k, False, timeout_ms)
                            await log_request(s, channel.id, key.id, model, 0, 0, timeout_ms, 0, False, "timeout", is_stream, source_ip)
                    continue
                except Exception as e:
                    logger.error(f"Key {key.id} forwarding error: {e}")
                    async with get_db_session() as s:
                        k = await s.get(Key, key.id)
                        if k:
                            await update_key_stats(s, k, False, 0)
                            await log_request(s, channel.id, key.id, model, 0, 0, 0, 0, False, str(e), is_stream, source_ip)
                    continue

    raise HTTPException(503, f"All keys exhausted after {MAX_RETRY_COUNT} retries")


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    return await proxy_request(request, "/v1/chat/completions", body)


@router.post("/v1/completions")
async def completions(request: Request):
    body = await request.json()
    return await proxy_request(request, "/v1/completions", body)


@router.get("/v1/models")
async def list_models(request: Request):
    # Validate external ApiKey
    api_key_value = extract_api_key_from_request(request)
    if not api_key_value:
        raise HTTPException(status_code=401, detail="Authorization required. Provide a valid API key")

    async with get_db_session() as auth_session:
        await validate_api_key(api_key_value, auth_session)

    models_set = set()
    async with get_db_session() as session:
        channels_result = await session.execute(select(Channel).where(Channel.enabled == True))
        channels = channels_result.scalars().all()
        proxy = PROXY_URL if PROXY_URL else None

        for channel in channels:
            keys_result = await session.execute(
                select(Key).where(Key.channel_id == channel.id, Key.status == "active").limit(1)
            )
            key = keys_result.scalar_one_or_none()
            if not key:
                continue
            url = channel.base_url.rstrip("/") + "/v1/models"
            headers = {"Authorization": f"Bearer {key.value}"}
            try:
                async with httpx.AsyncClient(timeout=10, proxy=proxy) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        for m in data.get("data", []):
                            models_set.add(m.get("id", ""))
            except Exception:
                continue

    models_list = [{"id": m, "object": "model", "owned_by": "keyrouter"} for m in sorted(models_set)]
    return JSONResponse(content={"object": "list", "data": models_list})

