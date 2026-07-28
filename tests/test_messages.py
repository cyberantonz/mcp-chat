import uuid

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError

from source.models import MAX_MESSAGE_LENGTH
from tests.conftest import call, register_agent


async def make_chat(client: Client[FastMCPTransport], purpose: str) -> tuple[str, tuple[str, str], tuple[str, str]]:
    """Two registered agents and a chat between them: (chat_id, (name_a, key_a), (name_b, key_b))."""
    name_a, key_a = await register_agent(client, f"{purpose}-a")
    name_b, key_b = await register_agent(client, f"{purpose}-b")
    data = await call(client, "create_chat", agent_name=name_a, secret_key=key_a, peer_name=name_b)
    return data["chat_id"], (name_a, key_a), (name_b, key_b)


async def test_send_and_get_messages(client: Client[FastMCPTransport]) -> None:
    chat_id, (name_a, key_a), (name_b, key_b) = await make_chat(client, "msg")
    sent = await call(client, "send_message", agent_name=name_a, secret_key=key_a, chat_id=chat_id, text="hello")
    await call(client, "send_message", agent_name=name_b, secret_key=key_b, chat_id=chat_id, text="hi back")

    data = await call(client, "get_messages", agent_name=name_a, secret_key=key_a, chat_id=chat_id)
    assert [(m["name"], m["text"]) for m in data["messages"]] == [(name_a, "hello"), (name_b, "hi back")]
    assert data["messages"][0]["message_id"] == sent["message_id"]
    assert all("created_at" in m for m in data["messages"])


async def test_message_ids_are_time_ordered(client: Client[FastMCPTransport]) -> None:
    chat_id, (name_a, key_a), _ = await make_chat(client, "order")
    for i in range(3):
        await call(client, "send_message", agent_name=name_a, secret_key=key_a, chat_id=chat_id, text=f"m{i}")
    data = await call(client, "get_messages", agent_name=name_a, secret_key=key_a, chat_id=chat_id)
    ids = [m["message_id"] for m in data["messages"]]
    assert ids == sorted(ids)  # UUIDv7: lexicographic == chronological


async def test_last_messages_limits_to_most_recent(client: Client[FastMCPTransport]) -> None:
    chat_id, (name_a, key_a), _ = await make_chat(client, "lastn")
    for i in range(5):
        await call(client, "send_message", agent_name=name_a, secret_key=key_a, chat_id=chat_id, text=f"m{i}")

    last_2 = await call(client, "get_messages", agent_name=name_a, secret_key=key_a, chat_id=chat_id, last_messages=2)
    assert [m["text"] for m in last_2["messages"]] == ["m3", "m4"]

    everything = await call(
        client, "get_messages", agent_name=name_a, secret_key=key_a, chat_id=chat_id, last_messages=0
    )
    assert len(everything["messages"]) == 5

    more_than_count = await call(
        client, "get_messages", agent_name=name_a, secret_key=key_a, chat_id=chat_id, last_messages=100
    )
    assert len(more_than_count["messages"]) == 5


async def test_identical_texts_have_distinct_message_ids(client: Client[FastMCPTransport]) -> None:
    chat_id, (name_a, key_a), _ = await make_chat(client, "dup-text")
    for _ in range(2):
        await call(client, "send_message", agent_name=name_a, secret_key=key_a, chat_id=chat_id, text="ping")
    data = await call(client, "get_messages", agent_name=name_a, secret_key=key_a, chat_id=chat_id, last_messages=1)
    all_messages = await call(client, "get_messages", agent_name=name_a, secret_key=key_a, chat_id=chat_id)
    assert len({m["message_id"] for m in all_messages["messages"]}) == 2
    assert data["messages"][0]["message_id"] == all_messages["messages"][-1]["message_id"]


async def test_non_participant_cannot_access_chat(client: Client[FastMCPTransport]) -> None:
    chat_id, _, _ = await make_chat(client, "intruder")
    name_c, key_c = await register_agent(client, "intruder-c")
    with pytest.raises(ToolError, match="chat_not_found"):
        await call(client, "get_messages", agent_name=name_c, secret_key=key_c, chat_id=chat_id)
    with pytest.raises(ToolError, match="chat_not_found"):
        await call(client, "send_message", agent_name=name_c, secret_key=key_c, chat_id=chat_id, text="sneak")


async def test_nonexistent_chat(client: Client[FastMCPTransport]) -> None:
    name, key = await register_agent(client, "nochat")
    with pytest.raises(ToolError, match="chat_not_found"):
        await call(client, "get_messages", agent_name=name, secret_key=key, chat_id=uuid.uuid7().hex)


async def test_malformed_chat_id_rejected_by_schema(client: Client[FastMCPTransport]) -> None:
    name, key = await register_agent(client, "badchatid")
    with pytest.raises(ToolError):
        await call(client, "get_messages", agent_name=name, secret_key=key, chat_id="zzz")


async def test_message_length_cap(client: Client[FastMCPTransport]) -> None:
    chat_id, (name_a, key_a), _ = await make_chat(client, "cap")
    await call(
        client, "send_message", agent_name=name_a, secret_key=key_a, chat_id=chat_id, text="x" * MAX_MESSAGE_LENGTH
    )
    with pytest.raises(ToolError):
        await call(
            client,
            "send_message",
            agent_name=name_a,
            secret_key=key_a,
            chat_id=chat_id,
            text="x" * (MAX_MESSAGE_LENGTH + 1),
        )
    with pytest.raises(ToolError):
        await call(client, "send_message", agent_name=name_a, secret_key=key_a, chat_id=chat_id, text="")
