from fastapi import Depends, FastAPI, HTTPException
from passlib.context import CryptContext
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas
from .database import engine, get_db

models.Base.metadata.create_all(engine)

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"])

# Example: get connection (health check)
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}

