import asyncio
import secrets
from pathlib import Path

import bcrypt

# system wordlist: present on macOS; installed by the `wamerican` package in the image
WORDLIST_PATHS = ("/usr/share/dict/words", "/usr/share/dict/american-english")
MIN_WORD_LENGTH = 4
# five words plus dashes must stay below bcrypt's 72-byte input limit
MAX_WORD_LENGTH = 10
KEY_WORDS = 5


def _load_words() -> tuple[str, ...]:
    for path in WORDLIST_PATHS:
        file = Path(path)
        if file.exists():
            words = {
                word
                for word in file.read_text().split()
                if MIN_WORD_LENGTH <= len(word) <= MAX_WORD_LENGTH
                and word.isascii()
                and word.isalpha()
                and word.islower()
            }
            return tuple(sorted(words))
    raise RuntimeError(f"no system wordlist found; looked at {WORDLIST_PATHS}")


WORDS = _load_words()


def generate_key() -> str:
    return "-".join(secrets.choice(WORDS) for _ in range(KEY_WORDS))


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
