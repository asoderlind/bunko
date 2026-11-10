"""Database engine and session management."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# FastAPI runs sync endpoints in a thread pool. SQLite is sufficient for this
# single-user deployment when WAL mode and a busy timeout are enabled; the
# tagging loop runs as one additional background thread in the same process.
_engine_options = {
    "pool_pre_ping": True,
    "future": True,
}

if settings.database_url.startswith("sqlite"):
    _engine_options["connect_args"] = {
        "check_same_thread": False,
        "timeout": 30,
    }
else:
    raise RuntimeError("Only SQLite is supported by this deployment")

engine = create_engine(settings.database_url, **_engine_options)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
