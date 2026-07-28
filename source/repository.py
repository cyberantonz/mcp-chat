import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from source.orm import Agent, Chat, ChatMessage


class AgentNameTakenError(Exception):
    pass


async def create_agent(session: AsyncSession, name: str, key_hash: str) -> Agent:
    agent = Agent(name=name, key_hash=key_hash)
    session.add(agent)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise AgentNameTakenError(name) from exc
    return agent


async def get_agent_by_name(session: AsyncSession, name: str) -> Agent | None:
    result = await session.execute(select(Agent).where(Agent.name == name))
    return result.scalar_one_or_none()


async def create_chat(session: AsyncSession, agent_id_1: uuid.UUID, agent_id_2: uuid.UUID) -> Chat:
    chat = Chat(agent_id_1=agent_id_1, agent_id_2=agent_id_2)
    session.add(chat)
    await session.flush()
    return chat


async def get_chat(session: AsyncSession, chat_id: uuid.UUID) -> Chat | None:
    return await session.get(Chat, chat_id)


async def add_message(session: AsyncSession, chat_id: uuid.UUID, sender_id: uuid.UUID, text: str) -> ChatMessage:
    message = ChatMessage(chat_id=chat_id, sender_id=sender_id, text=text)
    session.add(message)
    await session.flush()
    return message


async def get_messages(session: AsyncSession, chat_id: uuid.UUID, last_messages: int) -> list[tuple[ChatMessage, str]]:
    """Messages of a chat with sender names, ascending by creation time.

    With ``last_messages > 0`` only the N most recent are returned (still ascending).
    """
    stmt = (
        select(ChatMessage, Agent.name)
        .join(Agent, ChatMessage.sender_id == Agent.id)
        .where(ChatMessage.chat_id == chat_id)
    )
    if last_messages > 0:
        stmt = stmt.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(last_messages)
        rows = list((await session.execute(stmt)).tuples())
        rows.reverse()
    else:
        stmt = stmt.order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        rows = list((await session.execute(stmt)).tuples())
    return rows


async def list_chats(
    session: AsyncSession, agent_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[tuple[Chat, str]], int]:
    """One page of the agent's chats with peer names, plus the total count."""
    is_participant = or_(Chat.agent_id_1 == agent_id, Chat.agent_id_2 == agent_id)
    total = (await session.execute(select(func.count()).select_from(Chat).where(is_participant))).scalar_one()
    agent_1 = aliased(Agent)
    agent_2 = aliased(Agent)
    stmt = (
        select(Chat, agent_1.name, agent_2.name)
        .join(agent_1, agent_1.id == Chat.agent_id_1)
        .join(agent_2, agent_2.id == Chat.agent_id_2)
        .where(is_participant)
        .order_by(Chat.created_at.asc(), Chat.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).tuples()
    return [(chat, name_2 if chat.agent_id_1 == agent_id else name_1) for chat, name_1, name_2 in rows], total
