import threading
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app import notifications
from app.database import SessionLocal
from app.main import app
from app.models import IrrigationSchedule, Notification, SensorReading
from app.routers import schedules

AT_8 = datetime(2026, 11, 20, 8, 0)  # the review's "now" in the greenhouse zone (plan §5)


def entry(db, user_id, day=date(2026, 11, 20), at=time(8, 0), active=True):
    """A calendar entry written straight to the table: the API refuses moments already past."""
    row = IrrigationSchedule(created_by=user_id, irrigation_date=day, irrigation_time=at, is_active=active)
    db.add(row)
    db.commit()
    return row.id


def notes(db):
    db.expire_all()
    return db.query(Notification).order_by(Notification.id).all()


# FR-1 — Recordatorio de riego

def test_104_fr1a_due_and_late_entries_remind_their_owner(db, account):
    _, a_id = account("a@example.com")
    entry(db, a_id, at=time(8, 0))                     # due right now
    entry(db, a_id, day=date(2026, 11, 19))            # a day late: the system was off (D3)
    entry(db, a_id, at=time(8, 1))                     # not yet
    notifications.send_due_reminders(db, datetime(2026, 11, 20, 7, 59))
    late_only = notes(db)
    notifications.send_due_reminders(db, AT_8)
    assert [(n.user_id, n.type, n.is_read) for n in late_only] == [(a_id, "irrigation_reminder", False)]
    assert [(n.user_id, n.type, n.is_read) for n in notes(db)] == [(a_id, "irrigation_reminder", False)] * 2


def test_104_fr1b_one_reminder_per_entry_and_moment(db, account):
    _, a_id = account("a@example.com")
    entry(db, a_id)
    notifications.send_due_reminders(db, AT_8)
    notifications.send_due_reminders(db, AT_8.replace(hour=9))
    assert len(notes(db)) == 1

    entry(db, a_id, at=time(7, 0))
    start = threading.Barrier(2)

    def review():
        with SessionLocal() as own:
            start.wait()
            notifications.send_due_reminders(own, AT_8)

    runs = [threading.Thread(target=review) for _ in range(2)]
    for t in runs:
        t.start()
    for t in runs:
        t.join()
    assert len(notes(db)) == 2  # two reviews at once still remind the second entry once


def test_104_fr1c_moving_an_entry_allows_a_new_reminder(client, db, account, monkeypatch):
    monkeypatch.setattr(schedules, "local_now", lambda: datetime(2026, 11, 13, 10, 0))  # so 20-11 is future
    a, _ = account("a@example.com")
    sid = client.post("/schedules", json={"irrigation_date": "2026-11-20", "irrigation_time": "08:00"},
                      headers=a).json()["id"]
    notifications.send_due_reminders(db, AT_8)
    client.patch(f"/schedules/{sid}", json={"is_active": False}, headers=a)
    client.patch(f"/schedules/{sid}", json={"is_active": True, "irrigation_time": "08:00"}, headers=a)  # same moment
    notifications.send_due_reminders(db, AT_8.replace(hour=10))
    assert len(notes(db)) == 1  # reactivating or resending the same moment is not a new appointment (D6)

    assert client.patch(f"/schedules/{sid}", json={"irrigation_time": "09:00"}, headers=a).status_code == 200
    notifications.send_due_reminders(db, AT_8.replace(hour=9))
    assert [n.message[-18:] for n in notes(db)] == ["(20-11-2026 08:00)", "(20-11-2026 09:00)"]


def test_104_fr1d_inactive_entry_not_reminded(db, account):
    _, a_id = account("a@example.com")
    entry(db, a_id, day=date(2026, 11, 19), active=False)
    notifications.send_due_reminders(db, AT_8)
    assert notes(db) == []


def test_104_fr1e_reminder_message(db, account):
    _, a_id = account("a@example.com")
    entry(db, a_id)
    notifications.send_due_reminders(db, AT_8)
    assert [n.message for n in notes(db)] == ["Es hora de regar las orquídeas (20-11-2026 08:00)"]


# FR-2 — Alerta por lectura fuera de rango

HUMIDITY = {"name": "Humedad invernadero 1", "type": "humidity", "connection_type": "wifi",
            "reading_interval_minutes": 60}  # limits default to 70–90 % (102 D2)


def new_sensor(client, headers, **over):
    return client.post("/sensors", json={**HUMIDITY, **over}, headers=headers).json()


def send(client, sensor, *values):
    for v in values:
        r = client.post(f"/sensors/{sensor['id']}/readings", json={"value": v},
                        headers={"X-Sensor-Key": sensor["ingest_key"]})
        assert r.status_code == 201, (v, r.json())


def alerts(db):
    return [n for n in notes(db) if n.type == "reading_alert"]


def test_104_fr2a_leaving_the_range_alerts_the_owner(client, db, account):
    a, a_id = account("a@example.com")
    b, b_id = account("b@example.com")
    first = new_sensor(client, a)              # no readings yet
    was_in = new_sensor(client, b)
    send(client, was_in, 80)
    edge = new_sensor(client, a, name="Borde")
    send(client, edge, 70, 90)                 # equal to a limit is inside (D5)
    send(client, first, 65)
    send(client, was_in, 65)
    assert [(n.user_id, n.is_read) for n in alerts(db)] == [(a_id, False), (b_id, False)]


def test_104_fr2b_staying_out_does_not_alert_again(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    send(client, s, 65, 60)
    assert len(alerts(db)) == 1
    send(client, s, 80, 65)                    # back in, then out again: a new alert
    assert len(alerts(db)) == 2


def test_104_fr2c_empty_limit_has_no_bound_on_that_side(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    client.patch(f"/sensors/{s['id']}", json={"min_val": None}, headers=a)
    send(client, s, -50)
    assert alerts(db) == []
    send(client, s, 95)
    assert len(alerts(db)) == 1
    free = new_sensor(client, a, name="Sin límites")
    client.patch(f"/sensors/{free['id']}", json={"min_val": None, "max_val": None}, headers=a)
    send(client, free, -999, 999)
    assert len(alerts(db)) == 1


def test_104_fr2d_alert_message_names_sensor_value_and_limits(client, db, account):
    a, _ = account("a@example.com")
    send(client, new_sensor(client, a), 65)
    temp = new_sensor(client, a, name="Temperatura 1", type="temperature")
    client.patch(f"/sensors/{temp['id']}", json={"min_val": None}, headers=a)  # only the upper limit left
    send(client, temp, 25.5)
    assert [n.message for n in alerts(db)] == [
        "Humedad invernadero 1: 65 % fuera de rango (mín 70 %, máx 90 %)",
        "Temperatura 1: 25.5 °C fuera de rango (máx 24 °C)",
    ]


def test_104_fr2e_failed_alert_keeps_the_reading(client, db, account, monkeypatch):
    def broken(*args):
        raise RuntimeError("no se pudo crear la alerta")

    monkeypatch.setattr(notifications, "alert_if_out_of_range", broken)
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    send(client, s, 65)  # asserts 201
    db.expire_all()
    assert [r.value for r in db.query(SensorReading).all()] == [Decimal("65")]


# FR-3 — Ver mis notificaciones

def note(db, user_id, minute=0, is_read=False):
    """A notification written straight to the table at a chosen moment."""
    row = Notification(user_id=user_id, type="irrigation_reminder", message=f"aviso {minute}", is_read=is_read,
                       created_at=datetime(2026, 11, 20, minute // 60, minute % 60, tzinfo=timezone.utc))
    db.add(row)
    db.commit()
    return row.id


def mine(client, headers, **params):
    r = client.get("/notifications", params=params, headers=headers)
    assert r.status_code == 200
    return r.json()


def test_104_fr3a_newest_100_with_their_fields(client, db, account):
    a, a_id = account("a@example.com")
    for minute in range(120):
        note(db, a_id, minute)
    body = mine(client, a)
    assert [n["message"] for n in body] == [f"aviso {m}" for m in range(119, 19, -1)]
    assert set(body[0]) == {"id", "type", "message", "is_read", "created_at"}
    assert (body[0]["type"], body[0]["is_read"]) == ("irrigation_reminder", False)


def test_104_fr3b_unread_only_hides_read_ones(client, db, account):
    a, a_id = account("a@example.com")
    read = note(db, a_id, 1, is_read=True)
    unread = note(db, a_id, 2)
    assert [n["id"] for n in mine(client, a, unread_only="true")] == [unread]
    assert [n["id"] for n in mine(client, a)] == [unread, read]
    assert [n["id"] for n in mine(client, a, unread_only="false")] == [unread, read]


def test_104_fr3c_other_users_notifications_omitted(client, db, account):
    a, a_id = account("a@example.com")
    _, b_id = account("b@example.com")
    own = note(db, a_id, 1)
    note(db, b_id, 2)
    assert [n["id"] for n in mine(client, a)] == [own]


# FR-4 — Marcar como leída

def test_104_fr4a_mark_own_notification_read_twice(client, db, account):
    a, a_id = account("a@example.com")
    nid = note(db, a_id)
    first = client.patch(f"/notifications/{nid}/read", headers=a)
    again = client.patch(f"/notifications/{nid}/read", headers=a)
    assert (first.status_code, again.status_code) == (200, 200)
    assert first.json() == again.json()
    assert (first.json()["id"], first.json()["is_read"]) == (nid, True)
    assert [n.is_read for n in notes(db)] == [True]


def test_104_fr4b_other_users_or_missing_notification_not_found(client, db, account):
    a, _ = account("a@example.com")
    _, b_id = account("b@example.com")
    theirs = note(db, b_id)
    for nid in (theirs, theirs + 1000):
        r = client.patch(f"/notifications/{nid}/read", headers=a)
        assert (r.status_code, r.json()["detail"]) == (404, "Notificación no encontrada"), nid
    assert [n.is_read for n in notes(db)] == [False]


def test_104_security_routes_need_token(client):
    assert client.get("/notifications").status_code == 401
    assert client.patch("/notifications/1/read").status_code == 401
    paths = client.get("/openapi.json").json()["paths"]
    assert {m for p, ops in paths.items() if p.startswith("/notifications") for m in ops} == {"get", "patch"}
    # only the system creates notifications: no public route posts one (NFR Security)


# Timeliness NFR: a reminder appears at most 60 s after its moment while the system runs

def test_104_timeliness_review_every_60_seconds():
    assert notifications.REVIEW_EVERY_S == 60


def test_104_timeliness_app_runs_review_survives_errors_and_stops(monkeypatch):
    calls, second = [], threading.Event()

    def review(db, now):
        calls.append(now)
        if len(calls) == 1:
            raise RuntimeError("base caída")  # one failed review must not stop the next ones
        second.set()

    monkeypatch.setattr(notifications, "send_due_reminders", review)
    monkeypatch.setattr(notifications, "REVIEW_EVERY_S", 0.01)
    with TestClient(app):  # runs the lifespan: starts the loop, then cancels it on exit
        assert second.wait(5)
    assert calls[0].tzinfo is None  # greenhouse wall time, like the stored entries (D3)
