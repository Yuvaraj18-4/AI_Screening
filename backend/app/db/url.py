from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_database_url(url: str) -> str:
    """Normalizes database URLs for SQLAlchemy async engines (asyncpg and aiosqlite).

    Transforms Neon / Render style postgres URLs:
    - postgresql:// -> postgresql+asyncpg://
    - postgres:// -> postgresql+asyncpg://
    - converts sslmode=... to ssl=...
    - strips unsupported asyncpg parameters like channel_binding=...
    - ensures sqlite URLs use sqlite+aiosqlite://
    """
    if not url or not isinstance(url, str):
        return url

    # Handle sqlite explicitly to avoid urllib urlunparse custom scheme slashes issue
    if ":memory:" in url:
        return "sqlite+aiosqlite:///:memory:"

    if url.startswith("sqlite:///./shortlist.db") or url.startswith("sqlite+aiosqlite:///./shortlist.db"):
        from pathlib import Path
        root_db = (Path(__file__).resolve().parents[3] / "shortlist.db").as_posix()
        return f"sqlite+aiosqlite:///{root_db}"

    if url.startswith("sqlite:///"):
        return "sqlite+aiosqlite:///" + url[len("sqlite:///") :]
    if url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + url[len("sqlite://") :]
    if url.startswith("sqlite+aiosqlite://"):
        return url

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("postgresql", "postgres"):
        new_scheme = "postgresql+asyncpg"
    elif scheme == "sqlite":
        new_scheme = "sqlite+aiosqlite"
    else:
        new_scheme = scheme

    # Parse and clean query parameters
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # Convert sslmode -> ssl for asyncpg
    if "sslmode" in query_params:
        mode = query_params.pop("sslmode")
        if mode in ("require", "verify-ca", "verify-full", "prefer"):
            query_params["ssl"] = mode
        elif mode == "disable":
            query_params["ssl"] = "disable"

    # Remove parameters that asyncpg does not accept in query string
    query_params.pop("channel_binding", None)

    new_query = urlencode(query_params)
    return urlunparse(parsed._replace(scheme=new_scheme, query=new_query))
