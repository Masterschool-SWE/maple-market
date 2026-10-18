"""Database engine, session dependency, and table creation."""
from pathlib import Path
from typing import Iterator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from .config import DATABASE_URL, SQLITE_PATH

# Create the SQLite file's parent dir (works for both ./data and /data in Docker).
if DATABASE_URL.startswith("sqlite"):
    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

# check_same_thread=False lets the SQLite connection be shared across FastAPI threads.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def create_db_and_tables() -> None:
    """Create all tables declared on SQLModel subclasses (idempotent)."""
    SQLModel.metadata.create_all(engine)
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(product)")).fetchall()]
            if cols and "category" not in cols:
                conn.execute(text("ALTER TABLE product ADD COLUMN category VARCHAR DEFAULT 'General'"))
                conn.commit()


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session per request."""
    with Session(engine) as session:
        yield session
