from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.security import (
    check_login_rate_limit,
    clear_login_attempts,
    hash_password,
    record_failed_login,
    verify_password,
)
from app.db.models import User


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    rate_limit_key: str,
) -> User:
    check_login_rate_limit(rate_limit_key)

    query = select(User).where(User.email == email.lower().strip())
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        record_failed_login(rate_limit_key)
        raise UnauthorizedError("Invalid email or password")

    clear_login_attempts(rate_limit_key)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    query = select(User).where(User.email == email.lower().strip())
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    name: str,
    role: str,
    client_id: int | None = None,
) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        name=name,
        role=role,
        client_id=client_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
