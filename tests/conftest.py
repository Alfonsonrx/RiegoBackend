import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Point the app's engine at the test database before app.database is imported (002 plan D4).
load_dotenv()
_test_db = os.getenv("TEST_DB_NAME")
if not _test_db:
    pytest.exit("Falta TEST_DB_NAME en el entorno / .env", returncode=2)
if _test_db == os.getenv("DB_NAME", "db_riego"):
    pytest.exit("TEST_DB_NAME no puede ser la base real: las pruebas la vacían", returncode=2)
os.environ["DB_NAME"] = _test_db

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.main import app
from app.models import Base


@pytest.fixture(scope="session")
def alembic_cfg():
    return Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))


@pytest.fixture(scope="session", autouse=True)
def _schema(alembic_cfg):
    """Rebuild the test database from the migrations once per run, whatever the last run left (002 D6)."""
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session
