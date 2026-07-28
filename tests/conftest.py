"""Shared fixtures: in-memory MCP client over the real server and real database.

Isolation model (see DESIGN.md): all tests share one persistent, migrated
database. Every test registers its own agents under unique names, and data is
only reachable through its owners' credentials, so tests cannot observe each
other - including tests from previous runs and parallel xdist workers. Never
assert on global state, only on state owned by agents the test created.
"""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport

from source.server import mcp


@pytest.fixture
async def client() -> AsyncIterator[Client[FastMCPTransport]]:
    async with Client(mcp) as c:
        yield c


def unique_name(purpose: str) -> str:
    return f"test-{purpose}-{uuid.uuid7().hex}"


async def call(client: Client[FastMCPTransport], tool: str, **arguments: Any) -> dict[str, Any]:
    result = await client.call_tool(tool, arguments)
    assert result.structured_content is not None
    return result.structured_content


async def register_agent(client: Client[FastMCPTransport], purpose: str) -> tuple[str, str]:
    """Register a uniquely named agent; returns (name, secret_key)."""
    name = unique_name(purpose)
    data = await call(client, "register", name=name)
    return name, data["secret_key"]
