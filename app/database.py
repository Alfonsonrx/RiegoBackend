import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

load_dotenv()

engine = create_engine(
    URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PW", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "db_riego"),
    ),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    with SessionLocal() as db:
        yield db
