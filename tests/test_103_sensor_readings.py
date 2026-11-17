from datetime import datetime, timezone
from decimal import Decimal

from app.models import SensorReading

BAD_KEY = "Clave de sensor inválida"
INACTIVE = "Sensor inactivo"
HUMIDITY = {"name": "Humedad invernadero 1", "type": "humidity", "connection_type": "wifi",
            "reading_interval_minutes": 15}


def new_sensor(client, headers, **over):
    """A sensor of the account behind `headers`; returns its creation answer (with `ingest_key`)."""
    return client.post("/sensors", json={**HUMIDITY, **over}, headers=headers).json()


def send(client, sensor_id, key, value=78.5, headers=None):
    """What a device does: one value, its sensor's key in `X-Sensor-Key`."""
    sent = {} if key is None else {"X-Sensor-Key": key}
    return client.post(f"/sensors/{sensor_id}/readings", json={"value": value}, headers={**sent, **(headers or {})})


def readings(db):
    db.expire_all()
    return db.query(SensorReading).order_by(SensorReading.id).all()


# FR-1 — Recibir una lectura

def test_103_fr1a_reading_saved_with_reception_time(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    before = datetime.now(timezone.utc)
    assert send(client, s["id"], s["ingest_key"], 78.5).status_code == 201
    after = datetime.now(timezone.utc)
    [row] = readings(db)
    assert (row.sensor_id, row.value) == (s["id"], Decimal("78.5"))
    assert before <= row.recorded_at <= after


def test_103_fr1b_answer_has_reading_and_current_interval(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a, reading_interval_minutes=15)
    body = send(client, s["id"], s["ingest_key"], 78.5).json()
    [row] = readings(db)
    assert set(body) == {"id", "sensor_id", "value", "recorded_at", "reading_interval_minutes"}
    assert (body["id"], body["sensor_id"], body["value"], body["reading_interval_minutes"]) == \
        (row.id, s["id"], 78.5, 15)
    assert datetime.fromisoformat(body["recorded_at"]) == row.recorded_at


def test_103_fr1c_bad_missing_replaced_key_or_unknown_sensor_rejected(client, db, account):
    a, _ = account("a@example.com")
    b, _ = account("b@example.com")
    s = new_sensor(client, a)
    other = new_sensor(client, b)
    old_key = s["ingest_key"]
    new_key = client.post(f"/sensors/{s['id']}/ingest-key", headers=a).json()["ingest_key"]
    attempts = {
        "missing key": send(client, s["id"], None),
        "other sensor's key": send(client, s["id"], other["ingest_key"]),
        "replaced key": send(client, s["id"], old_key),
        "unknown sensor": send(client, other["id"] + 1000, new_key),
        "huge sensor id": send(client, 99999999999999999999, new_key),
        "owner's token instead of key": send(client, s["id"], None, headers=a),
    }
    assert {name: (r.status_code, r.json()["detail"]) for name, r in attempts.items()} == \
        {name: (401, BAD_KEY) for name in attempts}
    assert readings(db) == []


def test_103_fr1d_inactive_sensor_rejected(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    client.patch(f"/sensors/{s['id']}", json={"is_active": False}, headers=a)
    r = send(client, s["id"], s["ingest_key"])
    assert (r.status_code, r.json()["detail"]) == (403, INACTIVE)
    assert readings(db) == []


def test_103_fr1e_value_not_fitting_numeric_5_2_rejected(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    for value in (1000, -1000, 1.234, "caliente", None):
        assert send(client, s["id"], s["ingest_key"], value).status_code == 422, value
    assert readings(db) == []
    assert send(client, s["id"], s["ingest_key"], -999.99).status_code == 201  # the edge still fits


def test_103_fr1f_saved_readings_never_change(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    for value in (71.0, 72.5):
        send(client, s["id"], s["ingest_key"], value)
    before = [(r.id, r.sensor_id, r.value, r.recorded_at) for r in readings(db)]
    client.patch(f"/sensors/{s['id']}", json={"reading_interval_minutes": 5, "min_val": 75}, headers=a)
    client.patch(f"/sensors/{s['id']}", json={"is_active": False}, headers=a)
    client.post(f"/sensors/{s['id']}/ingest-key", headers=a)
    assert len(before) == 2
    assert [(r.id, r.sensor_id, r.value, r.recorded_at) for r in readings(db)] == before
    paths = client.get("/openapi.json").json()["paths"]
    reading_methods = {m for path, ops in paths.items() if "readings" in path for m in ops}
    assert reading_methods == {"get", "post"}


# FR-2 — Historial de un sensor

NOV = [datetime(2026, 11, d, 12, 0, tzinfo=timezone.utc) for d in (11, 12, 13)]


def stored(db, sensor_id, moments, value=Decimal("80")):
    """Readings at chosen moments, written straight to the table (the API stamps reception time)."""
    db.add_all(SensorReading(sensor_id=sensor_id, value=value, recorded_at=m) for m in moments)
    db.commit()


def history(client, headers, sensor_id, **params):
    return client.get(f"/sensors/{sensor_id}/readings", params=params, headers=headers)


def moments(response):
    return [datetime.fromisoformat(r["recorded_at"]) for r in response.json()]


def test_103_fr2a_history_newest_first(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    stored(db, s["id"], [NOV[1], NOV[2], NOV[0]])
    r = history(client, a, s["id"])
    assert moments(r) == [NOV[2], NOV[1], NOV[0]]
    first = r.json()[0]
    assert set(first) == {"id", "sensor_id", "value", "recorded_at"}
    assert (first["sensor_id"], first["value"]) == (s["id"], 80.0)


def test_103_fr2b_range_bounds_inclusive(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    stored(db, s["id"], NOV)
    nov12 = "2026-11-12T09:00:00-03:00"  # the same instant as NOV[1], in another zone
    assert moments(history(client, a, s["id"], start=nov12)) == [NOV[2], NOV[1]]
    assert moments(history(client, a, s["id"], end=nov12)) == [NOV[1], NOV[0]]
    assert moments(history(client, a, s["id"], start=nov12, end=nov12)) == [NOV[1]]
    assert moments(history(client, a, s["id"])) == [NOV[2], NOV[1], NOV[0]]


def test_103_fr2b_moment_without_zone_rejected(client, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    assert history(client, a, s["id"], start="2026-11-12T09:00:00").status_code == 422
    assert history(client, a, s["id"], end="2026-11-12T09:00:00").status_code == 422


def test_103_fr2c_at_most_limit_default_100(client, db, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    minutes = [datetime(2026, 11, 1, m // 60, m % 60, tzinfo=timezone.utc) for m in range(150)]
    stored(db, s["id"], minutes)
    assert len(history(client, a, s["id"]).json()) == 100
    assert moments(history(client, a, s["id"], limit=5)) == minutes[:-6:-1]  # the 5 newest


def test_103_fr2d_limit_over_1000_rejected(client, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    assert history(client, a, s["id"], limit=1001).status_code == 422
    assert history(client, a, s["id"], limit=0).status_code == 422
    assert history(client, a, s["id"], limit=1000).status_code == 200


def test_103_fr2e_start_after_end_rejected(client, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    r = history(client, a, s["id"], start="2026-11-13T00:00:00Z", end="2026-11-12T00:00:00Z")
    assert r.status_code == 422


def test_103_fr2f_other_users_or_missing_sensor_not_found(client, db, account):
    a, _ = account("a@example.com")
    b, _ = account("b@example.com")
    theirs = new_sensor(client, b)
    stored(db, theirs["id"], NOV)
    for sensor_id in (theirs["id"], theirs["id"] + 1000):
        r = history(client, a, sensor_id)
        assert (r.status_code, r.json()["detail"]) == (404, "Sensor no encontrado"), sensor_id


# FR-3 — Condiciones actuales

TEMPERATURE = {"name": "Temperatura 1", "type": "temperature", "connection_type": "bluetooth",
               "reading_interval_minutes": 30}


def conditions(client, headers):
    r = client.get("/conditions", headers=headers)
    assert r.status_code == 200
    return r.json()


def test_103_fr3a_each_active_sensor_with_its_last_reading(client, db, account):
    a, _ = account("a@example.com")
    hum = new_sensor(client, a)
    temp = new_sensor(client, a, **TEMPERATURE, min_val=17.5)
    stored(db, hum["id"], [NOV[2]], Decimal("81.5"))
    stored(db, hum["id"], [NOV[0], NOV[1]], Decimal("75"))  # older, though written later
    stored(db, temp["id"], [NOV[1]], Decimal("-0.5"))
    body = conditions(client, a)
    assert [{k: c[k] for k in c if k != "recorded_at"} for c in body] == [
        {"sensor_id": hum["id"], "name": "Humedad invernadero 1", "type": "humidity", "unit": "%",
         "min_val": 70.0, "max_val": 90.0, "value": 81.5},
        {"sensor_id": temp["id"], "name": "Temperatura 1", "type": "temperature", "unit": "°C",
         "min_val": 17.5, "max_val": 24.0, "value": -0.5},
    ]
    assert [datetime.fromisoformat(c["recorded_at"]) for c in body] == [NOV[2], NOV[1]]


def test_103_fr3b_sensor_without_readings_has_empty_value(client, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    [c] = conditions(client, a)
    assert (c["sensor_id"], c["value"], c["recorded_at"]) == (s["id"], None, None)


def test_103_fr3c_inactive_and_other_users_sensors_omitted(client, db, account):
    a, _ = account("a@example.com")
    b, _ = account("b@example.com")
    mine = new_sensor(client, a)
    off = new_sensor(client, a, name="Apagado")
    theirs = new_sensor(client, b)
    stored(db, off["id"], [NOV[0]])
    stored(db, theirs["id"], [NOV[0]])
    client.patch(f"/sensors/{off['id']}", json={"is_active": False}, headers=a)
    assert [c["sensor_id"] for c in conditions(client, a)] == [mine["id"]]


def test_103_security_queries_need_token(client, account):
    a, _ = account("a@example.com")
    s = new_sensor(client, a)
    for path in (f"/sensors/{s['id']}/readings", "/conditions"):
        assert client.get(path).status_code == 401, path
