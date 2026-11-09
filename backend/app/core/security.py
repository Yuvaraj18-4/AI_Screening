import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings
from app.core.errors import RateLimitError

ph = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None


# Simple in-memory rate limiter for login attempts (max 5 failures per 5 minutes per key)
_login_attempts: dict[str, list[float]] = defaultdict(list)


def check_login_rate_limit(key: str, max_attempts: int = 5, window_seconds: int = 300) -> None:
    now = time.time()
    attempts = [t for t in _login_attempts[key] if now - t < window_seconds]
    _login_attempts[key] = attempts
    if len(attempts) >= max_attempts:
        raise RateLimitError("Too many login attempts. Please wait 5 minutes.")


def record_failed_login(key: str) -> None:
    _login_attempts[key].append(time.time())


def clear_login_attempts(key: str) -> None:
    if key in _login_attempts:
        del _login_attempts[key]
