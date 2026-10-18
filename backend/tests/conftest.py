"""Pytest fixtures. Hermetic: isolated DB + fake embeddings, so tests need no API keys."""
import os
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-32b")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_shopassistant.db"
os.environ["EMBEDDING_MODEL"] = "fake:256"
os.environ["CHROMA_DIR"] = "./data/test_chroma"
os.environ["WORLDBOOK_DIR"] = str(Path(__file__).resolve().parents[2] / "assets" / "policies")

Path("data").mkdir(parents=True, exist_ok=True)
for name in (
    "test_shopassistant.db",
    "test_shopassistant.db-wal",
    "test_shopassistant.db-shm",
):
    Path("data", name).unlink(missing_ok=True)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from sqlmodel import SQLModel

    from app.database import engine
    from app.main import app

    SQLModel.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c
