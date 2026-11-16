import importlib.util
import os

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.database import engine, get_db
from app.main import app
from app.models import Base, User

TABLES = {"users", "sensors", "sensor_readings", "irrigation_schedule", "notifications"}


def _fresh(name):
    """Run a module again in a new namespace, as a process start would; sys.modules is untouched."""
    spec = importlib.util.find_spec(name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _users():
    with engine.connect() as conn:
        return conn.execute(select(User.__table__)).all()


def test_002_runs_against_test_database(db):
    assert db.execute(text("SELECT current_database()")).scalar() == os.environ["TEST_DB_NAME"]


def test_002_fr1a_records_survive_restart(db):
    db.add(User(name="Ana", email="ana@example.com", password_hash="x"))
    db.commit()
    engine.dispose()
    restarted = _fresh("app.database")
    try:
        with restarted.SessionLocal() as session:
            assert session.scalars(select(User.email)).all() == ["ana@example.com"]
    finally:
        restarted.engine.dispose()


def _app_tables():
    return TABLES & set(inspect(engine).get_table_names())


def test_002_fr1b_migrations_create_missing_structure(alembic_cfg):
    assert engine.url.database == os.environ["TEST_DB_NAME"]  # only ever drop the test database
    command.downgrade(alembic_cfg, "base")
    assert not _app_tables()
    command.upgrade(alembic_cfg, "head")  # also leaves the structure for the next tests
    assert _app_tables() == TABLES
    with engine.connect() as conn:  # exactly the structure the code expects (`alembic check`)
        context = MigrationContext.configure(conn, opts={"compare_server_default": True})
        assert compare_metadata(context, Base.metadata) == []


def test_002_fr1c_migrations_keep_existing_records(db, alembic_cfg):
    db.add(User(name="Ana", email="ana@example.com", password_hash="x"))
    db.commit()
    before = _users()
    command.upgrade(alembic_cfg, "head")
    assert _users() == before


def test_002_fr1d_startup_leaves_structure_alone(alembic_cfg):
    command.downgrade(alembic_cfg, "base")
    try:
        _fresh("app.main")
        assert not _app_tables()
    finally:
        command.upgrade(alembic_cfg, "head")


def test_002_fr2a_db_check_ok_without_token(client):
    r = client.get("/db-check")
    assert "authorization" not in r.request.headers  # 002 FR-2.c: no token sent
    assert r.status_code == 200
    assert r.json() == {"db": "ok"}


def test_002_fr2b_db_check_not_ok_when_db_unreachable(monkeypatch):
    dead = sessionmaker(bind=create_engine(
        engine.url.set(host="127.0.0.1", port=1), connect_args={"connect_timeout": 2}))

    def dead_db():
        with dead() as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_db, dead_db)
    r = TestClient(app, raise_server_exceptions=False).get("/db-check")
    assert r.status_code == 500


def test_002_fr3a_connection_from_environment(monkeypatch):
    for name, value in {"DB_HOST": "db.test", "DB_PORT": "6543", "DB_NAME": "riego_x",
                        "DB_USER": "u_test", "DB_PW": "pw_test"}.items():
        monkeypatch.setenv(name, value)
    url = _fresh("app.database").engine.url
    matches = [url.host == "db.test", url.port == 6543, url.database == "riego_x",
               url.username == "u_test", url.password == "pw_test"]
    assert all(matches), matches  # booleans only: never print the URL
