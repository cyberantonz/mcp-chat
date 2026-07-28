AUTH_FAILED = (
    "auth_failed: unknown agent name or wrong secret key. Verify the agent name and the secret key "
    "returned by `register`. Keys cannot be recovered - if yours is lost, register a new agent."
)

SELF_CHAT_FORBIDDEN = (
    "self_chat_forbidden: peer_name must be a different agent - you cannot create a chat with yourself."
)


def agent_name_taken(name: str) -> str:
    return (
        f"agent_name_taken: agent name '{name}' is already registered. Names cannot be re-registered "
        f"and keys cannot be rotated - choose a different name."
    )


def agent_not_found(peer_name: str) -> str:
    return (
        f"agent_not_found: no agent named '{peer_name}' is registered. Check the spelling; "
        f"the peer must call `register` first."
    )


def chat_not_found(chat_id: str) -> str:
    return (
        f"chat_not_found: chat '{chat_id}' does not exist or you are not one of its participants. "
        f"Use `list_chats` to see your chats."
    )


def invalid_chat_id(chat_id: str) -> str:
    return (
        f"invalid_chat_id: '{chat_id}' is not a valid chat id. Pass the 32-character hex id "
        f"returned by `create_chat` or listed by `list_chats`."
    )


def rate_limited(scope: str, limit: int, window_seconds: float, retry_after_seconds: float) -> str:
    return (
        f"rate_limited: more than {limit} requests per {window_seconds:g} seconds {scope}. "
        f"Retry after {retry_after_seconds:.1f} seconds."
    )
