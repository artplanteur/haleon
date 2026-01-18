from pathlib import Path
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine


DB_DIR = Path("C:/python/db")
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "haleon.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables (only if they don't exist)."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session."""
    with Session(engine) as session:
        yield session
