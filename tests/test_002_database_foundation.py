import os

from sqlalchemy import text


def test_002_runs_against_test_database(db):
    assert db.execute(text("SELECT current_database()")).scalar() == os.environ["TEST_DB_NAME"]
