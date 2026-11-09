from collections.abc import AsyncGenerator, Callable
from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def verify_csrf(
    request: Request,
    x_requested_with: Annotated[str | None, Header()] = None,
) -> None:
    """Mutating requests require an X-Requested-With header (CSRF defence)."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and (
        not x_requested_with or x_requested_with.lower() not in ("xmlhttprequest", "fetch")
    ):
        raise ForbiddenError("Missing or invalid X-Requested-With header")


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie(alias=settings.COOKIE_NAME)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = access_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise UnauthorizedError("Authentication required")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedError("Invalid or expired session")

    user_id = payload.get("sub")
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid session payload") from None

    query = select(User).where(User.id == user_id_int)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("User no longer exists")

    return user


def require_role(*allowed_roles: str) -> Callable[..., User]:
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError("Insufficient permissions")
        return current_user

    return role_checker
