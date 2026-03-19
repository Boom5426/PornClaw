from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


async def get_db() -> AsyncGenerator[Session, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    if "source_sessions" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("source_sessions")}
    additions = {
        "source_type": "ALTER TABLE source_sessions ADD COLUMN source_type VARCHAR(50) DEFAULT 'auto'",
        "adapter_name": "ALTER TABLE source_sessions ADD COLUMN adapter_name VARCHAR(100)",
        "context_json": "ALTER TABLE source_sessions ADD COLUMN context_json TEXT DEFAULT '{}'",
        "meta_json": "ALTER TABLE source_sessions ADD COLUMN meta_json TEXT DEFAULT '{}'",
    }
    with engine.begin() as connection:
        for column, ddl in additions.items():
            if column not in existing_columns:
                connection.execute(text(ddl))
