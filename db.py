import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import load_env

# Load the project-root .env before reading DATABASE_URL.
load_env()

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATABASE = f"sqlite:///{(PROJECT_ROOT / 'shopflow.local.db').as_posix()}"
URL = os.environ.get("DATABASE_URL") or DEFAULT_DATABASE

if URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if URL in ("sqlite://", "sqlite:///:memory:"):
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            URL,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(URL, connect_args=connect_args, pool_pre_ping=True)
else:
    engine = create_engine(URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
