import re

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError

from tests.conftest import call, unique_name


async def test_register_returns_key_and_id(client: Client[FastMCPTransport]) -> None:
    data = await call(client, "register", name=unique_name("register"))
    assert re.fullmatch(r"[a-z]+(-[a-z]+){4}", data["secret_key"])
    assert re.fullmatch(r"[0-9a-f]{32}", data["agent_id"])


async def test_register_keys_are_unique(client: Client[FastMCPTransport]) -> None:
    first = await call(client, "register", name=unique_name("uniq"))
    second = await call(client, "register", name=unique_name("uniq"))
    assert first["secret_key"] != second["secret_key"]
    assert first["agent_id"] != second["agent_id"]


async def test_register_duplicate_name_rejected(client: Client[FastMCPTransport]) -> None:
    name = unique_name("dup")
    await call(client, "register", name=name)
    with pytest.raises(ToolError, match="agent_name_taken"):
        await call(client, "register", name=name)


async def test_register_empty_name_rejected(client: Client[FastMCPTransport]) -> None:
    with pytest.raises(ToolError):
        await call(client, "register", name="")


async def test_register_too_long_name_rejected(client: Client[FastMCPTransport]) -> None:
    with pytest.raises(ToolError):
        await call(client, "register", name="x" * 129)
