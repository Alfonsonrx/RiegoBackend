from fastapi import Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import models, schemas
from .database import engine, get_db

@app.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(models.User)).all()

