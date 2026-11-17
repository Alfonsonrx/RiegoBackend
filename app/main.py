from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db
from .routers import auth, readings, schedules, sensors

# The schema comes only from migrations (`alembic upgrade head`); starting the app never touches it.
app = FastAPI()
app.include_router(auth.router)
app.include_router(schedules.router)
app.include_router(sensors.router)
app.include_router(readings.router)


# Health check: the database server answers. It does not tell whether the migrations were applied.
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}
