"""Notifications the system creates on its own (spec 104): irrigation reminders and reading alerts."""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal
from .routers.schedules import local_now

log = logging.getLogger(__name__)

REVIEW_EVERY_S = 60  # a reminder appears at most this long after its moment (NFR Timeliness)
REMINDER = "Es hora de regar las orquídeas ({:%d-%m-%Y %H:%M})"

# One atomic statement claims the due entries, so two reviews at once can't remind the same one (D2).
CLAIM_DUE = text("""
    UPDATE irrigation_schedule SET reminded_at = now()
    WHERE is_active AND reminded_at IS NULL AND irrigation_date + irrigation_time <= :now
    RETURNING created_by, irrigation_date, irrigation_time
""")


def send_due_reminders(db: Session, now: datetime) -> None:
    """Remind each active entry whose moment is `now` or earlier, once (FR-1). `now` is greenhouse wall time."""
    for user_id, day, at in db.execute(CLAIM_DUE, {"now": now}).all():
        db.add(models.Notification(user_id=user_id, type="irrigation_reminder",
                                   message=REMINDER.format(datetime.combine(day, at))))
    db.commit()


ALERT = "{name}: {value} {unit} fuera de rango ({limits})"


def _outside(value: Decimal, low: Decimal | None, high: Decimal | None) -> bool:
    """Limits are inclusive (D5); an empty one has no bound on that side (FR-2.c)."""
    return (low is not None and value < low) or (high is not None and value > high)


def _plain(number: Decimal) -> str:
    return format(number.normalize(), "f")  # 65.00 → "65", 25.50 → "25.5", 100 → "100"


def alert_if_out_of_range(db: Session, sensor: models.Sensor, reading: models.SensorReading) -> None:
    """Alert the owner when this reading takes the sensor out of its range (FR-2), not while it stays out (D2)."""
    low, high = sensor.min_val, sensor.max_val
    if not _outside(reading.value, low, high):
        return
    R = models.SensorReading
    previous = db.query(R.value).filter(R.sensor_id == sensor.id, R.id < reading.id).order_by(R.id.desc()).first()
    if previous is not None and _outside(previous.value, low, high):
        return
    limits = ", ".join(f"{word} {_plain(v)} {sensor.unit}" for word, v in (("mín", low), ("máx", high)) if v is not None)
    db.add(models.Notification(user_id=sensor.created_by, type="reading_alert", message=ALERT.format(
        name=sensor.name, value=_plain(reading.value), unit=sensor.unit, limits=limits)))
    db.commit()


def _review_once() -> None:
    with SessionLocal() as db:
        send_due_reminders(db, local_now())


async def review_loop() -> None:
    """Runs for the app's whole life (D1); the lifespan in main.py starts and cancels it."""
    while True:
        try:
            await asyncio.to_thread(_review_once)
        except Exception:  # a database hiccup must not end the reminders for good
            log.exception("La revisión de recordatorios falló; se reintenta en %s s", REVIEW_EVERY_S)
        await asyncio.sleep(REVIEW_EVERY_S)
