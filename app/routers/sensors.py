import hashlib
import secrets
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, get_owned_or_404

router = APIRouter(prefix="/sensors", tags=["Sensores"])

LIMITS_ORDER = "El límite inferior no puede ser mayor que el superior"
NOT_FOUND = "Sensor no encontrado"


def hash_key(key: str) -> str:
    """What is stored for an ingest key (D1); 103 compares against it."""
    return hashlib.sha256(key.encode()).hexdigest()


def new_key() -> tuple[str, str]:
    """A fresh ingest key (256 random bits) and its hash."""
    key = secrets.token_urlsafe(32)
    return key, hash_key(key)


def check_limits(low: Decimal | None, high: Decimal | None) -> None:
    if low is not None and high is not None and low > high:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, LIMITS_ORDER)


@router.post("", response_model=schemas.SensorCreated, status_code=status.HTTP_201_CREATED)
def create_sensor(
    sensor: schemas.SensorCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    kind = schemas.SENSOR_TYPES[sensor.type]
    low = kind["min_val"] if sensor.min_val is None else sensor.min_val
    high = kind["max_val"] if sensor.max_val is None else sensor.max_val
    check_limits(low, high)
    key, key_hash = new_key()
    row = models.Sensor(
        **sensor.model_dump(exclude={"min_val", "max_val"}),
        created_by=user.id, unit=kind["unit"], min_val=low, max_val=high, ingest_key_hash=key_hash,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return schemas.SensorCreated(**schemas.SensorOut.model_validate(row).model_dump(), ingest_key=key)


@router.get("", response_model=list[schemas.SensorOut])
def list_sensors(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Sensor).filter(models.Sensor.created_by == user.id).order_by(models.Sensor.id).all()


def owned_sensor(db: Session, sensor_id: int, user: models.User) -> models.Sensor:
    return get_owned_or_404(db, models.Sensor, models.Sensor.created_by, sensor_id, user, NOT_FOUND)


@router.get("/{sensor_id}", response_model=schemas.SensorOut)
def get_sensor(sensor_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return owned_sensor(db, sensor_id, user)


@router.patch("/{sensor_id}", response_model=schemas.SensorOut)
def update_sensor(
    sensor_id: int,
    change: schemas.SensorUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    row = owned_sensor(db, sensor_id, user)
    sent = change.model_dump(exclude_unset=True)
    check_limits(sent.get("min_val", row.min_val), sent.get("max_val", row.max_val))  # sent mixed with stored (D3)
    for field, value in sent.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{sensor_id}/ingest-key", response_model=schemas.IngestKeyOut)
def regenerate_ingest_key(
    sensor_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    row = owned_sensor(db, sensor_id, user)
    key, row.ingest_key_hash = new_key()  # the old key stops working (103 FR-1.c)
    db.commit()
    return {"ingest_key": key}
