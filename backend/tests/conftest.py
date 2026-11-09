from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.models import Client, User
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_client_org(db_session: AsyncSession) -> Client:
    client = Client(name="Acme Corp")
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    return client


@pytest.fixture
async def sample_client_org_2(db_session: AsyncSession) -> Client:
    client = Client(name="Beta Retail")
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    return client


@pytest.fixture
async def recruiter_user(db_session: AsyncSession) -> User:
    user = User(
        email="recruiter@example.com",
        password_hash=hash_password("recruiter123"),
        name="Test Recruiter",
        role="recruiter",
        client_id=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def client_user(db_session: AsyncSession, sample_client_org: Client) -> User:
    user = User(
        email="client@example.com",
        password_hash=hash_password("client123"),
        name="Test Client User",
        role="client",
        client_id=sample_client_org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def client_user_2(db_session: AsyncSession, sample_client_org_2: Client) -> User:
    user = User(
        email="client2@example.com",
        password_hash=hash_password("client123"),
        name="Other Client User",
        role="client",
        client_id=sample_client_org_2.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_cookie_for(user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {settings.COOKIE_NAME: token}
