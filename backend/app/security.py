"""Password hashing, session tokens, team codes and lightweight rate limiting."""
from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
from collections import defaultdict, deque

import bcrypt

from .config import settings

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous I/O/0/1
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MOBILE_RE = re.compile(r"^[0-9+\-() ]{7,20}$")


def hash_password(password: str) -> str:
    if len(password) > 72:
        # bcrypt has a 72-byte input limit; pre-hash longer values.
        password = hashlib.sha256(password.encode()).hexdigest()
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        if len(password) > 72:
            password = hashlib.sha256(password.encode()).hexdigest()
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(36)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_team_code() -> str:
    return "TNX-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


def new_public_team_id(seq: int) -> str:
    return f"TNX-{seq:04d}"


def valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value or ""))


def valid_mobile(value: str) -> bool:
    return bool(MOBILE_RE.match(value or ""))


def password_strength(value: str) -> tuple[bool, str]:
    if len(value) < 10:
        return False, "Password must be at least 10 characters long."
    classes = sum([
        bool(re.search(r"[a-z]", value)),
        bool(re.search(r"[A-Z]", value)),
        bool(re.search(r"[0-9]", value)),
        bool(re.search(r"[^A-Za-z0-9]", value)),
    ])
    if classes < 3:
        return False, "Use at least three of: lowercase, uppercase, digit, symbol."
    return True, ""


class RateLimiter:
    """In-process sliding window limiter. Use Redis in multi-worker deployments."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int | None = None, window: int = 60) -> bool:
        limit = limit or settings.rate_limit_per_minute
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < now - window:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key:
                self._hits.pop(key, None)
            else:
                self._hits.clear()


rate_limiter = RateLimiter()
