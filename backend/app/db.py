"""Database engine, session factory and initialisation helpers."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

BASE_DIR = Path(__file__).resolve().parent.parent

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - dialect specific
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=10000")
        cur.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and install portability guards/triggers."""
    from . import models  # noqa: F401  (register mappers before create_all)

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        if settings.is_sqlite:
            # SQLite has no partial CREATE INDEX ... WHERE with arbitrary boolean
            # expressions in older versions; triggers give us the same guarantee.
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS trg_team_exactly_two_insert
                BEFORE INSERT ON team_memberships
                BEGIN
                    SELECT CASE WHEN (SELECT COUNT(*) FROM team_memberships
                                      WHERE team_id = NEW.team_id) >= 2
                        THEN RAISE(ABORT, 'A team may contain exactly two members')
                    END;
                END
            """))
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS trg_team_exactly_two_update
                BEFORE UPDATE ON team_memberships
                WHEN NEW.team_id <> OLD.team_id
                BEGIN
                    SELECT CASE WHEN (SELECT COUNT(*) FROM team_memberships
                                      WHERE team_id = NEW.team_id) >= 2
                        THEN RAISE(ABORT, 'A team may contain exactly two members')
                    END;
                END
            """))
