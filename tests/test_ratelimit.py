import asyncio
from collections.abc import AsyncIterator

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError

from source.ratelimit import SlidingWindowLimiter
from source.server import rate_limiter
from tests.conftest import call, register_agent


def test_limiter_allows_up_to_limit() -> None:
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60.0)
    assert [limiter.acquire("k") for _ in range(3)] == [None, None, None]
    retry_after = limiter.acquire("k")
    assert retry_after is not None
    assert 0 < retry_after <= 60.0


def test_limiter_keys_are_independent() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60.0)
    assert limiter.acquire("a") is None
    assert limiter.acquire("b") is None
    assert limiter.acquire("a") is not None


async def test_limiter_window_slides() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_seconds=0.1)
    assert limiter.acquire("k") is None
    assert limiter.acquire("k") is None
    retry_after = limiter.acquire("k")
    assert retry_after is not None
    assert retry_after <= 0.1
    await asyncio.sleep(0.15)
    assert limiter.acquire("k") is None


@pytest.fixture
async def tight_agent_limit() -> AsyncIterator[int]:
    limit = 3
    original = rate_limiter._per_agent
    rate_limiter._per_agent = SlidingWindowLimiter(limit=limit, window_seconds=60.0)
    try:
        yield limit
    finally:
        rate_limiter._per_agent = original


async def test_agent_over_limit_is_rejected(client: Client[FastMCPTransport], tight_agent_limit: int) -> None:
    name, key = await register_agent(client, "ratelimit")  # consumes 1 of the budget
    for _ in range(tight_agent_limit - 1):
        await call(client, "list_chats", agent_name=name, secret_key=key)
    with pytest.raises(ToolError, match=r"rate_limited.*3 requests per 60 seconds.*Retry after \d+\.\d seconds"):
        await call(client, "list_chats", agent_name=name, secret_key=key)


async def test_limit_is_per_agent(client: Client[FastMCPTransport], tight_agent_limit: int) -> None:
    name_a, key_a = await register_agent(client, "ratelimit-a")
    for _ in range(tight_agent_limit - 1):
        await call(client, "list_chats", agent_name=name_a, secret_key=key_a)
    with pytest.raises(ToolError, match="rate_limited"):
        await call(client, "list_chats", agent_name=name_a, secret_key=key_a)

    name_b, key_b = await register_agent(client, "ratelimit-b")
    data = await call(client, "list_chats", agent_name=name_b, secret_key=key_b)
    assert data == {"chats": [], "total": 0}
