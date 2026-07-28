import asyncio
import base64
import secrets

import bcrypt

KEY_BYTES = 20  # 20 random bytes -> 32 base32 chars, no padding


def generate_key() -> str:
    """Return a new random secret key: 32 chars of the base32 alphabet."""
    return base64.b32encode(secrets.token_bytes(KEY_BYTES)).decode("ascii")


def _hash_key(key: str) -> str:
    return bcrypt.hashpw(key.encode("ascii"), bcrypt.gensalt()).decode("ascii")


def _verify_key(key: str, key_hash: str) -> bool:
    try:
        return bcrypt.checkpw(key.encode("ascii"), key_hash.encode("ascii"))
    except UnicodeEncodeError, ValueError:
        return False


# bcrypt is CPU-bound (~50-100 ms by design): keep it off the event loop
async def hash_key(key: str) -> str:
    return await asyncio.to_thread(_hash_key, key)


async def verify_key(key: str, key_hash: str) -> bool:
    return await asyncio.to_thread(_verify_key, key, key_hash)


# Verified against when the agent name does not exist, so that an
# unknown name costs the same time as a wrong key (no name probing).
DUMMY_KEY_HASH = _hash_key(generate_key())
