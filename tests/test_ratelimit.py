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
    assert [limiter.allow("k") for _ in range(4)] == [True, True, True, False]


def test_limiter_keys_are_independent() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60.0)
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")


async def test_limiter_window_slides() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_seconds=0.1)
    assert limiter.allow("k")
    assert limiter.allow("k")
    assert not limiter.allow("k")
    await asyncio.sleep(0.15)
    assert limiter.allow("k")


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
    with pytest.raises(ToolError, match="rate_limited"):
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
