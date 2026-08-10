from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base

_connect_args: dict = {}
if settings.database_is_sqlite:
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_sync_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Session:
    return SessionLocal()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_report_created_by()


def _migrate_report_created_by() -> None:
    """Add the `dd_reports.created_by` column to pre-existing databases.

    `Base.metadata.create_all` never alters existing tables, so deployments
    created before reports were linked to users need this one-off column.
    """
    inspector = inspect(engine)
    if "dd_reports" not in inspector.get_table_names():
        return
    if any(col["name"] == "created_by" for col in inspector.get_columns("dd_reports")):
        return
    if engine.dialect.name == "postgresql":
        ddl = "ALTER TABLE dd_reports ADD COLUMN IF NOT EXISTS created_by VARCHAR(36)"
    else:
        ddl = "ALTER TABLE dd_reports ADD COLUMN created_by VARCHAR(36)"
    with engine.begin() as conn:
        conn.execute(text(ddl))
