from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models
from .database import engine, get_db

models.Base.metadata.create_all(engine)

app = FastAPI()

# Example: get connection (health check)
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}
