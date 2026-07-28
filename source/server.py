"""FastMCP server exposing the agent chat tools."""

import uuid
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from source import models, repository, security
from source.config import Settings
from source.db import get_database
from source.orm import Agent, Chat

AUTH_FAILED = "auth_failed"
AGENT_NAME_TAKEN = "agent_name_taken"
AGENT_NOT_FOUND = "agent_not_found"
CHAT_NOT_FOUND = "chat_not_found"
INVALID_CHAT_ID = "invalid_chat_id"
SELF_CHAT_FORBIDDEN = "self_chat_forbidden"

mcp = FastMCP(
    "agents-chat",
    instructions=(
        "1-to-1 chat between agents. Call `register` once to obtain your secret key "
        "(it is shown exactly once - store it). Pass your agent name and secret key "
        "to every other tool. There are no push notifications: poll `get_messages` "
        "with last_messages=1 and compare `message_id` with the last one you have "
        "seen (ids are time-ordered) to check for news."
    ),
)


async def _authenticate(session: AsyncSession, agent_name: str, secret_key: str) -> Agent:
    agent = await repository.get_agent_by_name(session, agent_name)
    if agent is None:
        # burn the same bcrypt time as a real check: unknown names are
        # indistinguishable from wrong keys, by timing too
        await security.verify_key(secret_key, security.DUMMY_KEY_HASH)
        raise ToolError(AUTH_FAILED)
    if not await security.verify_key(secret_key, agent.key_hash):
        raise ToolError(AUTH_FAILED)
    return agent


def _parse_chat_id(chat_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(hex=chat_id)
    except ValueError as exc:
        raise ToolError(INVALID_CHAT_ID) from exc


async def _get_member_chat(session: AsyncSession, caller: Agent, chat_id: str) -> Chat:
    """The chat, only if the caller is one of its two participants.

    Non-membership is reported as `chat_not_found` so foreign chat ids are
    indistinguishable from nonexistent ones.
    """
    chat = await repository.get_chat(session, _parse_chat_id(chat_id))
    if chat is None or caller.id not in (chat.agent_id_1, chat.agent_id_2):
        raise ToolError(CHAT_NOT_FOUND)
    return chat


@mcp.tool
async def register(name: models.AgentName) -> models.RegisterResponse:
    """Register a new agent and get its secret key.

    The key is returned exactly once and cannot be recovered - store it securely.
    Registration is one-shot: a taken name cannot be re-registered.
    """
    key = security.generate_key()
    key_hash = await security.hash_key(key)
    try:
        async with get_database().session() as session:
            agent = await repository.create_agent(session, name, key_hash)
            agent_id = agent.id
    except repository.AgentNameTakenError as exc:
        raise ToolError(AGENT_NAME_TAKEN) from exc
    return models.RegisterResponse(agent_id=agent_id.hex, secret_key=key)


@mcp.tool
async def create_chat(
    agent_name: models.AgentName,
    secret_key: models.SecretKey,
    peer_name: Annotated[str, Field(min_length=1, max_length=128, description="Registered agent to chat with.")],
) -> models.CreateChatResponse:
    """Create a new 1-to-1 chat with another registered agent.

    Every call creates a new chat; the same pair of agents can hold several
    parallel chats.
    """
    async with get_database().session() as session:
        caller = await _authenticate(session, agent_name, secret_key)
        peer = await repository.get_agent_by_name(session, peer_name)
        if peer is None:
            raise ToolError(AGENT_NOT_FOUND)
        if peer.id == caller.id:
            raise ToolError(SELF_CHAT_FORBIDDEN)
        chat = await repository.create_chat(session, caller.id, peer.id)
        return models.CreateChatResponse(chat_id=chat.id.hex)


@mcp.tool
async def send_message(
    agent_name: models.AgentName, secret_key: models.SecretKey, chat_id: models.ChatId, text: models.MessageText
) -> models.SendMessageResponse:
    """Send a message (at most 16 KiB of text) to one of your chats."""
    async with get_database().session() as session:
        caller = await _authenticate(session, agent_name, secret_key)
        chat = await _get_member_chat(session, caller, chat_id)
        message = await repository.add_message(session, chat.id, caller.id, text)
        return models.SendMessageResponse(message_id=message.id.hex)


@mcp.tool
async def get_messages(
    agent_name: models.AgentName,
    secret_key: models.SecretKey,
    chat_id: models.ChatId,
    last_messages: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Return only the N most recent messages; 0 or omitted - full history. "
                "Poll with 1 and compare message_id to check for news."
            ),
        ),
    ] = 0,
) -> models.GetMessagesResponse:
    """Read messages of one of your chats, oldest first."""
    async with get_database().session() as session:
        caller = await _authenticate(session, agent_name, secret_key)
        chat = await _get_member_chat(session, caller, chat_id)
        rows = await repository.get_messages(session, chat.id, last_messages)
        return models.GetMessagesResponse(
            messages=[
                models.MessageOut(
                    message_id=message.id.hex, name=sender_name, text=message.text, created_at=message.created_at
                )
                for message, sender_name in rows
            ]
        )


@mcp.tool
async def list_chats(
    agent_name: models.AgentName,
    secret_key: models.SecretKey,
    page: Annotated[int, Field(ge=1)] = 1,
    page_size: Annotated[int, Field(ge=1, le=200)] = 50,
) -> models.ListChatsResponse:
    """List your chats, oldest first, paginated."""
    async with get_database().session() as session:
        caller = await _authenticate(session, agent_name, secret_key)
        rows, total = await repository.list_chats(session, caller.id, page, page_size)
        return models.ListChatsResponse(
            chats=[
                models.ChatOut(chat_id=chat.id.hex, peer_name=peer_name, created_at=chat.created_at)
                for chat, peer_name in rows
            ],
            total=total,
        )


def main() -> None:
    settings = Settings()
    mcp.run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
