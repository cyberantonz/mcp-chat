import re

import pytest
from fastmcp import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError

from tests.conftest import call, register_agent, unique_name


async def test_create_chat(client: Client[FastMCPTransport]) -> None:
    name_a, key_a = await register_agent(client, "chat-a")
    name_b, _ = await register_agent(client, "chat-b")
    data = await call(client, "create_chat", agent_name=name_a, secret_key=key_a, peer_name=name_b)
    assert re.fullmatch(r"[0-9a-f]{32}", data["chat_id"])


async def test_same_pair_can_have_multiple_chats(client: Client[FastMCPTransport]) -> None:
    name_a, key_a = await register_agent(client, "multi-a")
    name_b, _ = await register_agent(client, "multi-b")
    first = await call(client, "create_chat", agent_name=name_a, secret_key=key_a, peer_name=name_b)
    second = await call(client, "create_chat", agent_name=name_a, secret_key=key_a, peer_name=name_b)
    assert first["chat_id"] != second["chat_id"]


async def test_create_chat_with_unknown_peer(client: Client[FastMCPTransport]) -> None:
    name, key = await register_agent(client, "nopeer")
    with pytest.raises(ToolError, match="agent_not_found"):
        await call(client, "create_chat", agent_name=name, secret_key=key, peer_name=unique_name("ghost"))


async def test_create_chat_with_self_forbidden(client: Client[FastMCPTransport]) -> None:
    name, key = await register_agent(client, "selfchat")
    with pytest.raises(ToolError, match="self_chat_forbidden"):
        await call(client, "create_chat", agent_name=name, secret_key=key, peer_name=name)


async def test_list_chats_pagination_and_order(client: Client[FastMCPTransport]) -> None:
    name_a, key_a = await register_agent(client, "page-a")
    chat_ids = []
    for i in range(3):
        peer_name, _ = await register_agent(client, f"page-peer{i}")
        data = await call(client, "create_chat", agent_name=name_a, secret_key=key_a, peer_name=peer_name)
        chat_ids.append(data["chat_id"])

    page_1 = await call(client, "list_chats", agent_name=name_a, secret_key=key_a, page=1, page_size=2)
    page_2 = await call(client, "list_chats", agent_name=name_a, secret_key=key_a, page=2, page_size=2)
    assert page_1["total"] == page_2["total"] == 3
    assert len(page_1["chats"]) == 2
    assert len(page_2["chats"]) == 1
    listed = [chat["chat_id"] for chat in page_1["chats"] + page_2["chats"]]
    assert listed == chat_ids  # created_at ascending == creation order


async def test_list_chats_shows_peer_name_for_both_sides(client: Client[FastMCPTransport]) -> None:
    name_a, key_a = await register_agent(client, "sides-a")
    name_b, key_b = await register_agent(client, "sides-b")
    await call(client, "create_chat", agent_name=name_a, secret_key=key_a, peer_name=name_b)

    seen_by_a = await call(client, "list_chats", agent_name=name_a, secret_key=key_a)
    seen_by_b = await call(client, "list_chats", agent_name=name_b, secret_key=key_b)
    assert [chat["peer_name"] for chat in seen_by_a["chats"]] == [name_b]
    assert [chat["peer_name"] for chat in seen_by_b["chats"]] == [name_a]
    assert "created_at" in seen_by_a["chats"][0]


async def test_list_chats_page_past_the_end_keeps_total(client: Client[FastMCPTransport]) -> None:
    name_a, key_a = await register_agent(client, "pastend-a")
    name_b, _ = await register_agent(client, "pastend-b")
    await call(client, "create_chat", agent_name=name_a, secret_key=key_a, peer_name=name_b)
    data = await call(client, "list_chats", agent_name=name_a, secret_key=key_a, page=5, page_size=50)
    assert data == {"chats": [], "total": 1}


async def test_list_chats_empty(client: Client[FastMCPTransport]) -> None:
    name, key = await register_agent(client, "lonely")
    data = await call(client, "list_chats", agent_name=name, secret_key=key)
    assert data == {"chats": [], "total": 0}
