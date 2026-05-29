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
from database import get_session
from models import Key, Channel, RequestLog
from key_manager import select_key
from config import MAX_RETRY_COUNT, ROUTING_TIMEOUT, PROXY_URL
import httpx

logger = logging.getLogger("router")

router = APIRouter(tags=["proxy"])


async def stream_forward(
    channel: Channel,
    key: Key,
    path: str,
    body: dict,
    request_headers: dict,
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
                # Read full error body for non-streaming errors
                error_body = await resp.aread()
                elapsed = time.time() - start_time
                await update_key_stats(session, key, False, elapsed)
                try:
                    error_data = json.loads(error_body)
                    error_msg = error_data.get("error", {}).get("message", str(error_body[:200]))
                except Exception:
                    error_msg = error_body.decode()[:200]
                await log_request(session, channel.id, key.id, model, 0, 0, elapsed, status_code, error_msg, True)
                # Return error as JSON, not stream
                return None, error_body, status_code

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

            elapsed = time.time() - start_time

            async def generate():
                for c in chunks_collected:
                    yield c

            await update_key_stats(session, key, True, elapsed)
            await log_request(session, channel.id, key.id, model, prompt_tokens, completion_tokens, elapsed, status_code, None, True)

            return generate(), None, status_code


async def non_stream_forward(
    channel: Channel,
    key: Key,
    path: str,
    body: dict,
    request_headers: dict,
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
        elapsed = time.time() - start_time
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

        await update_key_stats(session, key, success, elapsed)
        await log_request(session, channel.id, key.id, model, prompt_tokens, completion_tokens, elapsed, status_code, error_msg, False)

        return resp, elapsed, status_code


async def log_request(
    session: AsyncSession,
    channel_id: int,
    key_id: int,
    model: Optional[str],
    prompt_tokens: int,
    completion_tokens: int,
    response_time: float,
    status_code: int,
    error_message: Optional[str],
    is_streaming: bool,
):
    log = RequestLog(
        channel_id=channel_id,
        key_id=key_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        response_time=response_time,
        status_code=status_code,
        error_message=error_message,
        is_streaming=is_streaming,
    )
    session.add(log)
    await session.commit()


async def update_key_stats(session: AsyncSession, key: Key, success: bool, response_time: float):
    key.last_used = datetime.now()
    key.total_requests += 1
    if success:
        key.success_requests += 1
        if key.avg_response_time == 0:
            key.avg_response_time = response_time
        else:
            key.avg_response_time = (key.avg_response_time * (key.success_requests - 1) + response_time) / key.success_requests
    else:
        key.error_count += 1
    await session.commit()


async def proxy_request(request: Request, path: str, body: dict):
    """Core proxy logic with retry and key selection."""
    is_stream = body.get("stream", False)
    model = body.get("model", None)
    attempted_keys = []

    for attempt in range(MAX_RETRY_COUNT):
        async with get_session() as session:
            # Find enabled channels
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
                        result = await stream_forward(channel, key, path, body, dict(request.headers), session)

                        generator, error_body, status_code = result
                        if generator is None:
                            # Stream request returned an error status
                            if status_code == 429:
                                logger.warning(f"Key {key.id} rate limited (stream), retrying...")
                                continue
                            elif status_code == 401:
                                async with get_session() as s:
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

                        return StreamingResponse(
                            generator(),
                            media_type="text/event-stream",
                            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                        )
                    else:
                        resp, elapsed, status_code = await non_stream_forward(channel, key, path, body, dict(request.headers), session)

                        if status_code < 400:
                            return JSONResponse(content=resp.json(), status_code=status_code)
                        elif status_code == 429:
                            logger.warning(f"Key {key.id} rate limited, retrying...")
                            continue
                        elif status_code >= 500:
                            logger.warning(f"Key {key.id} got {status_code}, retrying...")
                            continue
                        elif status_code == 401:
                            async with get_session() as s:
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
                    async with get_session() as s:
                        k = await s.get(Key, key.id)
                        if k:
                            await update_key_stats(s, k, False, ROUTING_TIMEOUT)
                            await log_request(s, channel.id, key.id, model, 0, 0, ROUTING_TIMEOUT, 0, "timeout", is_stream)
                    continue
                except Exception as e:
                    logger.error(f"Key {key.id} forwarding error: {e}")
                    async with get_session() as s:
                        k = await s.get(Key, key.id)
                        if k:
                            await update_key_stats(s, k, False, 0)
                            await log_request(s, channel.id, key.id, model, 0, 0, 0, 0, str(e), is_stream)
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
    models_set = set()
    async with get_session() as session:
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