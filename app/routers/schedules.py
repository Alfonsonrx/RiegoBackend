from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user, get_owned_or_404

router = APIRouter(prefix="/schedules", tags=["Calendario"])

NOT_FUTURE = "La fecha y hora de riego deben ser futuras"
NOT_FOUND = "Entrada de riego no encontrada"


def local_now() -> datetime:
    """Greenhouse wall clock (101 D4): naive, like the stored date and time. Tests replace it."""
    return datetime.now(ZoneInfo(get_settings().TIMEZONE)).replace(tzinfo=None)


def require_future(day: date, at: time) -> None:
    if datetime.combine(day, at) <= local_now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, NOT_FUTURE)


@router.post("", response_model=schemas.ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    entry: schemas.ScheduleCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    require_future(entry.irrigation_date, entry.irrigation_time)
    row = models.IrrigationSchedule(created_by=user.id, **entry.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=list[schemas.ScheduleOut])
def list_schedules(
    active_only: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    S = models.IrrigationSchedule
    query = db.query(S).filter(S.created_by == user.id)
    if active_only:
        query = query.filter(S.is_active)
    return query.order_by(S.irrigation_date, S.irrigation_time, S.id).all()


@router.patch("/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(
    schedule_id: int,
    change: schemas.ScheduleUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    S = models.IrrigationSchedule
    row = get_owned_or_404(db, S, S.created_by, schedule_id, user, NOT_FOUND)
    sent = change.model_dump(exclude_unset=True)
    day = sent.get("irrigation_date", row.irrigation_date)
    at = sent.get("irrigation_time", row.irrigation_time)
    if (day, at) != (row.irrigation_date, row.irrigation_time):  # same date and time resent: not a change (D8)
        require_future(day, at)
    for field, value in sent.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
