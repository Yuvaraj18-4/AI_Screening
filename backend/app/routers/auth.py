from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db, verify_csrf
from app.core.security import create_access_token
from app.db.models import User
from app.schemas.auth import UserLogin, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut, dependencies=[Depends(verify_csrf)])
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{credentials.email.lower()}"

    user = await auth_service.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password,
        rate_limit_key=rate_limit_key,
    )

    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )

    return UserOut.model_validate(user)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.model_validate(current_user)
