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
    for bad_key in ("only-four-words-here", "UPPER-case-not-a-word", "with-digit5-in-a-word"):
        with pytest.raises(ToolError):
            await call(client, "list_chats", agent_name=name, secret_key=bad_key)


async def test_key_roundtrip() -> None:
    key = security.generate_key()
    key_hash = await security.hash_key(key)
    assert await security.verify_key(key, key_hash)
    assert not await security.verify_key(security.generate_key(), key_hash)


def test_generated_key_is_five_wordlist_words() -> None:
    words = security.generate_key().split("-")
    assert len(words) == security.KEY_WORDS
    assert all(word in security.WORDS for word in words)
    assert all(security.MIN_WORD_LENGTH <= len(word) <= security.MAX_WORD_LENGTH for word in words)


def test_generated_keys_fit_bcrypt_input_limit() -> None:
    longest = max(len(word) for word in security.WORDS)
    assert security.KEY_WORDS * longest + security.KEY_WORDS - 1 <= 72
