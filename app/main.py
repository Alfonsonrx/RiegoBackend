import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import notifications
from .config import get_settings
from .database import get_db
from .routers import auth, notifications as notifications_routes, readings, schedules, sensors


@asynccontextmanager
async def lifespan(app: FastAPI):
    review = asyncio.create_task(notifications.review_loop())  # irrigation reminders (104 D1)
    yield
    review.cancel()
    with suppress(asyncio.CancelledError):
        await review


# The schema comes only from migrations (`alembic upgrade head`); starting the app never touches it.
app = FastAPI(lifespan=lifespan)
app.add_middleware(  # the web UI lives on another origin; bearer tokens, no cookies
    CORSMiddleware, allow_origins=get_settings().CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(schedules.router)
app.include_router(sensors.router)
app.include_router(readings.router)
app.include_router(notifications_routes.router)


# Health check: the database server answers. It does not tell whether the migrations were applied.
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}
