from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from .config import get_settings

settings = get_settings()
engine = create_engine(
    URL.create(
        "postgresql+psycopg2",
        username=settings.DB_USER,
        password=settings.DB_PW,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    ),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    with SessionLocal() as db:
        yield db
