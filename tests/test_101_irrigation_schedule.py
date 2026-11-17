from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.config import get_settings
from app.models import IrrigationSchedule
from app.routers import schedules

NOW = datetime(2026, 11, 13, 10, 0)  # greenhouse clock for these tests (plan §5)
NOT_FUTURE = "La fecha y hora de riego deben ser futuras"
NOT_FOUND = "Entrada de riego no encontrada"
FIELDS = {"id", "irrigation_date", "irrigation_time", "is_active"}


@pytest.fixture
def api(client, monkeypatch):
    monkeypatch.setattr(schedules, "local_now", lambda: NOW)
    return client


def account(client, email):
    """Register and log in; return (auth headers, user id)."""
    user = client.post("/auth/register", json={"name": "N", "email": email, "password": "orquidea-123"})
    login = client.post("/auth/login", data={"username": email, "password": "orquidea-123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user.json()["id"]


def create(client, headers, day="2026-11-20", at="08:00"):
    return client.post("/schedules", json={"irrigation_date": day, "irrigation_time": at}, headers=headers)


def add_row(db, owner, day, at, active=True):
    """An entry written straight to the DB (e.g. already expired, or inactive without the PATCH route)."""
    row = IrrigationSchedule(created_by=owner, irrigation_date=day, irrigation_time=at, is_active=active)
    db.add(row)
    db.commit()
    return row.id


def rows(db):
    db.expire_all()
    return db.query(IrrigationSchedule).order_by(IrrigationSchedule.id).all()


# FR-1 — Crear una entrada

def test_101_fr1a_create_active_entry_owned_by_caller(api, db):
    a, a_id = account(api, "a@example.com")
    assert create(api, a).status_code == 201
    [row] = rows(db)
    assert (row.created_by, row.irrigation_date, row.irrigation_time, row.is_active) == \
        (a_id, date(2026, 11, 20), time(8, 0), True)


def test_101_fr1b_create_returns_id_date_time_active(api):
    a, _ = account(api, "a@example.com")
    body = create(api, a).json()
    assert set(body) == FIELDS  # no owner id in the answer
    assert isinstance(body["id"], int)
    assert (body["irrigation_date"], body["irrigation_time"], body["is_active"]) == ("2026-11-20", "08:00:00", True)


def test_101_fr1c_missing_or_invalid_date_time_rejected(api, db):
    a, _ = account(api, "a@example.com")
    for payload in ({"irrigation_date": "2026-11-20"},                                  # no time
                    {"irrigation_time": "08:00"},                                       # no date
                    {"irrigation_date": "ayer-no", "irrigation_time": "08:00"},
                    {"irrigation_date": "2026-11-20", "irrigation_time": "25:00"},
                    {"irrigation_date": "2026-11-20", "irrigation_time": "08:00+02:00"}):  # not wall-clock
        assert api.post("/schedules", json=payload, headers=a).status_code == 422, payload
    assert rows(db) == []


def test_101_fr1d_now_or_past_rejected(api, db):
    a, _ = account(api, "a@example.com")
    for day, at in (("2026-11-13", "10:00"), ("2026-11-13", "09:00"), ("2026-11-12", "23:59")):
        r = create(api, a, day, at)
        assert (r.status_code, r.json()["detail"]) == (400, NOT_FUTURE), (day, at)
    assert rows(db) == []
    assert create(api, a, "2026-11-13", "10:01").status_code == 201  # one minute later is the future


def test_101_fr1d_now_is_greenhouse_wall_clock(monkeypatch):
    # A zone no test machine runs in (UTC+14): server time or UTC would be hours off.
    monkeypatch.setattr(get_settings(), "TIMEZONE", "Pacific/Kiritimati")
    expected = datetime.now(ZoneInfo("Pacific/Kiritimati")).replace(tzinfo=None)
    got = schedules.local_now()
    assert got.tzinfo is None
    assert abs((got - expected).total_seconds()) < 5


# FR-2 — Ver el calendario

def test_101_fr2a_list_ordered_by_date_then_time(api):
    a, _ = account(api, "a@example.com")
    for day, at in (("2026-11-21", "07:00"), ("2026-11-20", "18:00"), ("2026-11-20", "08:00"),
                    ("2026-11-20", "08:00")):  # repeated entries are allowed (D5), tie broken by id
        create(api, a, day, at)
    body = api.get("/schedules", headers=a).json()
    assert [(e["irrigation_date"], e["irrigation_time"]) for e in body] == [
        ("2026-11-20", "08:00:00"), ("2026-11-20", "08:00:00"), ("2026-11-20", "18:00:00"),
        ("2026-11-21", "07:00:00")]
    assert body[0]["id"] < body[1]["id"]
    assert all(set(e) == FIELDS for e in body)


def test_101_fr2b_list_omits_other_users_entries(api):
    a, _ = account(api, "a@example.com")
    b, _ = account(api, "b@example.com")
    mine = create(api, a).json()["id"]
    create(api, b, "2026-11-22", "06:00")
    assert [e["id"] for e in api.get("/schedules", headers=a).json()] == [mine]


def test_101_fr2c_active_only_hides_inactive(api, db):
    a, a_id = account(api, "a@example.com")
    active = add_row(db, a_id, date(2026, 11, 20), time(8, 0))
    inactive = add_row(db, a_id, date(2026, 11, 21), time(8, 0), active=False)
    assert [e["id"] for e in api.get("/schedules?active_only=true", headers=a).json()] == [active]
    assert [e["id"] for e in api.get("/schedules", headers=a).json()] == [active, inactive]


# FR-3 — Cambiar una entrada

def test_101_fr3a_change_time_then_deactivate(api, db):
    a, _ = account(api, "a@example.com")
    entry = create(api, a).json()["id"]
    r = api.patch(f"/schedules/{entry}", json={"irrigation_time": "09:30"}, headers=a)
    assert (r.status_code, r.json()) == (200, {"id": entry, "irrigation_date": "2026-11-20",
                                               "irrigation_time": "09:30:00", "is_active": True})
    r = api.patch(f"/schedules/{entry}", json={"is_active": False}, headers=a)
    assert (r.status_code, r.json()["is_active"], r.json()["irrigation_time"]) == (200, False, "09:30:00")
    [row] = rows(db)
    assert (row.irrigation_time, row.is_active) == (time(9, 30), False)


def test_101_fr3b_change_into_past_rejected(api, db):
    a, a_id = account(api, "a@example.com")
    entry = create(api, a, "2026-11-13", "11:00").json()["id"]
    for change in ({"irrigation_date": "2026-11-12"},   # new date, stored time
                   {"irrigation_time": "09:00"}):       # stored date, new time: 2026-11-13 09:00 < NOW
        r = api.patch(f"/schedules/{entry}", json=change, headers=a)
        assert (r.status_code, r.json()["detail"]) == (400, NOT_FUTURE), change
    [row] = rows(db)
    assert (row.irrigation_date, row.irrigation_time, row.is_active) == (date(2026, 11, 13), time(11, 0), True)
    expired = add_row(db, a_id, date(2026, 11, 1), time(8, 0))  # only the state changes: no date check
    assert api.patch(f"/schedules/{expired}", json={"is_active": False}, headers=a).status_code == 200


def test_101_fr3b_resending_same_date_time_is_not_a_change(api, db):
    a, a_id = account(api, "a@example.com")
    expired = add_row(db, a_id, date(2026, 11, 1), time(8, 0))
    full = {"irrigation_date": "2026-11-01", "irrigation_time": "08:00:00", "is_active": False}
    r = api.patch(f"/schedules/{expired}", json=full, headers=a)  # e.g. a form that sends every field
    assert (r.status_code, r.json()["is_active"]) == (200, False)


def test_101_fr3c_other_users_or_missing_entry_not_found(api, db):
    a, _ = account(api, "a@example.com")
    b, _ = account(api, "b@example.com")
    theirs = create(api, b).json()["id"]
    for entry in (theirs, theirs + 1000):
        r = api.patch(f"/schedules/{entry}", json={"is_active": False}, headers=a)
        assert (r.status_code, r.json()["detail"]) == (404, NOT_FOUND), entry
    [row] = rows(db)
    assert row.is_active is True


def test_101_fr3d_null_or_invalid_change_rejected(api, db):
    a, _ = account(api, "a@example.com")
    entry = create(api, a).json()["id"]
    for change in ({"irrigation_time": None}, {"irrigation_date": None}, {"is_active": None},
                   {"irrigation_time": "8 en punto"}):
        assert api.patch(f"/schedules/{entry}", json=change, headers=a).status_code == 422, change
    [row] = rows(db)
    assert (row.irrigation_date, row.irrigation_time, row.is_active) == (date(2026, 11, 20), time(8, 0), True)


# NFR Security: every route needs a token

def test_101_security_routes_need_token(api):
    for method, path in (("POST", "/schedules"), ("GET", "/schedules"), ("PATCH", "/schedules/1")):
        assert api.request(method, path, json={}).status_code == 401, (method, path)
