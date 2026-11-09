from app.db.url import normalize_database_url


def test_normalize_neon_database_url():
    neon_url = "postgresql://user:pass@ep-cool-sample.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    normalized = normalize_database_url(neon_url)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "ssl=require" in normalized
    assert "channel_binding" not in normalized
    assert "sslmode" not in normalized


def test_normalize_postgres_url_variants():
    # postgres:// scheme
    url = "postgres://user:secret@localhost:5432/shortlist_prod"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+asyncpg://")

    # postgresql:// with other ssl modes
    url_ca = "postgresql://user:secret@localhost:5432/shortlist_prod?sslmode=verify-full"
    normalized_ca = normalize_database_url(url_ca)
    assert normalized_ca.startswith("postgresql+asyncpg://")
    assert "ssl=verify-full" in normalized_ca
    assert "sslmode" not in normalized_ca


def test_normalize_sqlite_urls():
    normalized_shortlist = normalize_database_url("sqlite:///./shortlist.db")
    assert normalized_shortlist.startswith("sqlite+aiosqlite:///")
    assert normalized_shortlist.endswith("/shortlist.db")
    assert normalize_database_url("sqlite:///./other.db") == "sqlite+aiosqlite:///./other.db"
    assert normalize_database_url("sqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"
    assert normalize_database_url("sqlite+aiosqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"


def test_normalize_empty_or_already_normalized():
    assert normalize_database_url("") == ""
    assert normalize_database_url(None) is None
    already = "postgresql+asyncpg://user:pass@localhost:5432/mydb?ssl=require"
    assert normalize_database_url(already) == already
