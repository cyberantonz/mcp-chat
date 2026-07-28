import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError

from source import security
from tests.conftest import call, register_agent, unique_name


async def test_wrong_key_rejected(client: Client[FastMCPTransport]) -> None:
    name, key = await register_agent(client, "auth")
    wrong_key = security.generate_key()
    assert wrong_key != key
    with pytest.raises(ToolError, match="auth_failed"):
        await call(client, "list_chats", agent_name=name, secret_key=wrong_key)


async def test_unknown_agent_rejected(client: Client[FastMCPTransport]) -> None:
    with pytest.raises(ToolError, match="auth_failed"):
        await call(client, "list_chats", agent_name=unique_name("ghost"), secret_key=security.generate_key())


async def test_malformed_key_rejected_by_schema(client: Client[FastMCPTransport]) -> None:
    name, _ = await register_agent(client, "badkey")
    with pytest.raises(ToolError):
        await call(client, "list_chats", agent_name=name, secret_key="not-a-base32-key")


async def test_key_roundtrip() -> None:
    key = security.generate_key()
    key_hash = await security.hash_key(key)
    assert await security.verify_key(key, key_hash)
    assert not await security.verify_key(security.generate_key(), key_hash)
