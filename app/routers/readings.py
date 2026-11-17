import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from .sensors import hash_key, owned_sensor

router = APIRouter(tags=["Lecturas"])

BAD_KEY = "Clave de sensor inválida"
INACTIVE = "Sensor inactivo"
RANGE_ORDER = "El inicio no puede ser posterior al fin"
NEWEST_FIRST = (models.SensorReading.recorded_at.desc(), models.SensorReading.id.desc())


@router.post("/sensors/{sensor_id}/readings", response_model=schemas.IngestOut,
             status_code=status.HTTP_201_CREATED)
def receive_reading(
    sensor_id: int,
    reading: schemas.ReadingIn,
    x_sensor_key: Annotated[str | None, Header()] = None,  # optional so a missing key is 401, not 422 (D1)
    db: Session = Depends(get_db),
):
    sensor = db.get(models.Sensor, sensor_id)
    # ponytail: an unknown sensor skips the comparison, so timing tells it apart; with 256-bit keys
    # there is nothing useful to guess. Add a dummy compare_digest if that ever matters (D1).
    if sensor is None or x_sensor_key is None \
            or not hmac.compare_digest(hash_key(x_sensor_key), sensor.ingest_key_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_KEY)
    if not sensor.is_active:  # only someone holding the key learns the sensor is inactive (D3)
        raise HTTPException(status.HTTP_403_FORBIDDEN, INACTIVE)
    row = models.SensorReading(sensor_id=sensor.id, value=reading.value)
    db.add(row)
    db.commit()
    db.refresh(row)  # recorded_at comes from the database clock (D2)
    # 104 hooks its out-of-range alert here, after the commit (D7).
    return schemas.IngestOut(**schemas.ReadingOut.model_validate(row).model_dump(),
                             reading_interval_minutes=sensor.reading_interval_minutes)


@router.get("/sensors/{sensor_id}/readings", response_model=list[schemas.ReadingOut])
def list_readings(
    sensor_id: int,
    start: AwareDatetime | None = None,  # an offset is required: a bare time is ambiguous (D4)
    end: AwareDatetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if start and end and start > end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, RANGE_ORDER)
    owned_sensor(db, sensor_id, user)
    query = db.query(models.SensorReading).filter(models.SensorReading.sensor_id == sensor_id)
    if start:
        query = query.filter(models.SensorReading.recorded_at >= start)
    if end:
        query = query.filter(models.SensorReading.recorded_at <= end)
    return query.order_by(*NEWEST_FIRST).limit(limit).all()


@router.get("/conditions", response_model=list[schemas.ConditionOut])
def current_conditions(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    sensors = db.query(models.Sensor).filter(
        models.Sensor.created_by == user.id, models.Sensor.is_active.is_(True)).order_by(models.Sensor.id).all()
    out = []
    for s in sensors:  # ponytail: one query per sensor; a person has few. DISTINCT ON if that grows (D5)
        last = db.query(models.SensorReading).filter(
            models.SensorReading.sensor_id == s.id).order_by(*NEWEST_FIRST).first()
        out.append(schemas.ConditionOut(
            sensor_id=s.id, name=s.name, type=s.type, unit=s.unit, min_val=s.min_val, max_val=s.max_val,
            value=last.value if last else None, recorded_at=last.recorded_at if last else None))
    return out
