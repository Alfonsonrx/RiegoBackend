from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models
from .database import engine, get_db
from .routers import auth

models.Base.metadata.create_all(engine)

app = FastAPI()
app.include_router(auth.router)

# Example: get connection (health check)
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}
