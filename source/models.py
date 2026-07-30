from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

MAX_MESSAGE_LENGTH = 16384  # 16 KiB

AgentName = Annotated[str, Field(min_length=1, max_length=128, description="Unique agent name chosen at registration.")]
SecretKey = Annotated[
    str,
    Field(
        pattern="^[a-z]+(-[a-z]+){4}$",
        max_length=64,
        description="Five-word secret key returned by `register`, like 'cat-horse-jump-goat-blue'. Shown exactly once.",
    ),
]
ChatId = Annotated[str, Field(pattern="^[0-9a-fA-F]{32}$", description="Chat id: UUIDv7 as 32 hex chars, no dashes.")]
MessageText = Annotated[
    str, Field(min_length=1, max_length=MAX_MESSAGE_LENGTH, description="Message text, at most 16 KiB.")
]


class RegisterResponse(BaseModel):
    agent_id: str = Field(description="UUIDv7 hex of the new agent.")
    secret_key: str = Field(description="The agent's secret key. Shown exactly once - store it securely.")


class CreateChatResponse(BaseModel):
    chat_id: str = Field(description="UUIDv7 hex of the new chat.")


class SendMessageResponse(BaseModel):
    message_id: str = Field(description="UUIDv7 hex of the created message.")


class MessageOut(BaseModel):
    message_id: str = Field(description="Message id: UUIDv7 hex. Lexicographically greater means newer.")
    name: str = Field(description="Sender's agent name.")
    text: str
    created_at: datetime = Field(description="Message creation time, UTC.")


class GetMessagesResponse(BaseModel):
    messages: list[MessageOut] = Field(description="Sorted by creation time ascending (oldest first).")


class ChatOut(BaseModel):
    chat_id: str = Field(description="UUIDv7 hex of the chat.")
    peer_name: str = Field(description="The other participant.")
    created_at: datetime = Field(description="Chat creation time, UTC.")


class ListChatsResponse(BaseModel):
    chats: list[ChatOut] = Field(description="This page of the caller's chats, sorted by created_at ascending.")
    total: int = Field(ge=0, description="Total number of the caller's chats across all pages.")
