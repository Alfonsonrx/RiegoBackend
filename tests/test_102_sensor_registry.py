import hashlib
from decimal import Decimal

from app.models import Sensor

NOT_FOUND = "Sensor no encontrado"
OUT = {"id", "name", "type", "unit", "connection_type", "reading_interval_minutes", "min_val", "max_val",
       "is_active"}
HUMIDITY = {"name": "Humedad invernadero 1", "type": "humidity", "connection_type": "wifi",
            "reading_interval_minutes": 60}


def create(client, headers, **over):
    return client.post("/sensors", json={**HUMIDITY, **over}, headers=headers)


def rows(db):
    db.expire_all()
    return db.query(Sensor).order_by(Sensor.id).all()


def sha256(key):
    return hashlib.sha256(key.encode()).hexdigest()


def limits(row):
    return row.min_val, row.max_val


# FR-1 — Registrar un sensor

def test_102_fr1a_create_active_sensor_owned_by_caller(client, db, account):
    a, a_id = account("a@example.com")
    assert create(client, a).status_code == 201
    [row] = rows(db)
    assert (row.created_by, row.name, row.type, row.connection_type, row.reading_interval_minutes,
            row.is_active) == (a_id, "Humedad invernadero 1", "humidity", "wifi", 60, True)


def test_102_fr1b_create_answers_data_and_key_once(client, account):
    a, _ = account("a@example.com")
    body = create(client, a).json()
    assert set(body) == OUT | {"ingest_key"}
    assert (body["name"], body["type"], body["unit"], body["connection_type"], body["reading_interval_minutes"],
            body["min_val"], body["max_val"], body["is_active"]) == \
        ("Humedad invernadero 1", "humidity", "%", "wifi", 60, 70.0, 90.0, True)
    assert isinstance(body["ingest_key"], str) and len(body["ingest_key"]) >= 43  # 256 random bits


def test_102_fr1c_key_stored_only_as_sha256(client, db, account):
    a, _ = account("a@example.com")
    key = create(client, a).json()["ingest_key"]
    [row] = rows(db)
    assert row.ingest_key_hash == sha256(key)
    assert key not in row.ingest_key_hash


def test_102_fr1d_unit_follows_type(client, account):
    a, _ = account("a@example.com")
    assert create(client, a).json()["unit"] == "%"
    assert create(client, a, type="temperature", unit="°F").json()["unit"] == "°C"  # a sent unit is ignored


def test_102_fr1e_missing_limits_take_type_defaults(client, account):
    a, _ = account("a@example.com")
    got = [create(client, a, **over).json() for over in
           ({}, {"min_val": 75}, {"max_val": 85.5}, {"type": "temperature"})]
    assert [(s["min_val"], s["max_val"]) for s in got] == [(70.0, 90.0), (75.0, 90.0), (70.0, 85.5), (18.0, 24.0)]


def test_102_fr1f_unknown_type_rejected(client, db, account):
    a, _ = account("a@example.com")
    for kind in ("soil_moisture", "Humidity", ""):
        assert create(client, a, type=kind).status_code == 422, kind
    assert rows(db) == []


def test_102_fr1g_unknown_connection_rejected(client, db, account):
    a, _ = account("a@example.com")
    for conn in ("lora", "WiFi", ""):
        assert create(client, a, connection_type=conn).status_code == 422, conn
    assert rows(db) == []


def test_102_fr1h_interval_must_be_whole_minutes_from_1(client, db, account):
    a, _ = account("a@example.com")
    for interval in (0, -5, 1.5, "diez", None, 2**31):  # 2**31 does not fit the column
        assert create(client, a, reading_interval_minutes=interval).status_code == 422, interval
    assert rows(db) == []
    assert create(client, a, reading_interval_minutes=1).status_code == 201


def test_102_fr1i_lower_limit_above_upper_rejected(client, db, account):
    a, _ = account("a@example.com")
    for over in ({"min_val": 95},                    # above the default upper 90
                 {"min_val": 50, "max_val": 40},
                 {"type": "temperature", "max_val": 10}):  # below the default lower 18
        assert create(client, a, **over).status_code == 422, over
    assert rows(db) == []
    assert create(client, a, min_val=80, max_val=80).status_code == 201  # equal limits are fine


def test_102_fr1j_limit_with_too_many_digits_rejected(client, db, account):
    a, _ = account("a@example.com")
    for over in ({"max_val": 1000}, {"min_val": 1.234}, {"min_val": "setenta"}):
        assert create(client, a, **over).status_code == 422, over
    assert rows(db) == []
    assert create(client, a, min_val=-999.99, max_val=999.99).status_code == 201


def test_102_fr1_name_required_and_fits(client, db, account):
    a, _ = account("a@example.com")
    for name in ("", "x" * 101, None):
        assert create(client, a, name=name).status_code == 422, name
    assert rows(db) == []


# FR-2 — Ver mis sensores

def test_102_fr2a_list_own_sensors_with_all_fields(client, account):
    a, _ = account("a@example.com")
    first = create(client, a).json()["id"]
    second = create(client, a, name="Temp 1", type="temperature", connection_type="bluetooth").json()["id"]
    body = client.get("/sensors", headers=a).json()
    assert [s["id"] for s in body] == [first, second]
    assert all(set(s) == OUT for s in body)
    assert (body[1]["type"], body[1]["unit"], body[1]["connection_type"]) == ("temperature", "°C", "bluetooth")


def test_102_fr2b_list_omits_other_users_sensors(client, account):
    a, _ = account("a@example.com")
    b, _ = account("b@example.com")
    mine = create(client, a).json()["id"]
    create(client, b)
    assert [s["id"] for s in client.get("/sensors", headers=a).json()] == [mine]


def test_102_fr2c_key_never_in_read_or_change_answers(client, account):
    a, _ = account("a@example.com")
    sensor = create(client, a).json()["id"]
    answers = [client.get("/sensors", headers=a).json()[0],
               client.get(f"/sensors/{sensor}", headers=a).json(),
               client.patch(f"/sensors/{sensor}", json={"name": "Otro"}, headers=a).json()]
    for body in answers:
        assert set(body) == OUT, body.keys()


def test_102_fr2d_get_own_sensor_by_id(client, account):
    a, _ = account("a@example.com")
    created = create(client, a).json()
    r = client.get(f"/sensors/{created['id']}", headers=a)
    assert r.status_code == 200
    assert r.json() == {k: v for k, v in created.items() if k != "ingest_key"}


def test_102_fr2e_other_users_or_missing_sensor_not_found(client, account):
    a, _ = account("a@example.com")
    b, _ = account("b@example.com")
    theirs = create(client, b).json()["id"]
    for sensor in (theirs, theirs + 1000):
        r = client.get(f"/sensors/{sensor}", headers=a)
        assert (r.status_code, r.json()["detail"]) == (404, NOT_FOUND), sensor


# FR-3 — Cambiar un sensor

def test_102_fr3a_change_name_interval_limits_state(client, db, account):
    a, _ = account("a@example.com")
    sensor = create(client, a).json()["id"]
    change = {"name": "Humedad norte", "reading_interval_minutes": 15, "min_val": 72.5, "max_val": 88,
              "is_active": False}
    r = client.patch(f"/sensors/{sensor}", json=change, headers=a)
    assert r.status_code == 200
    assert {k: r.json()[k] for k in change} == {**change, "max_val": 88.0}
    [row] = rows(db)
    assert (row.name, row.reading_interval_minutes, limits(row), row.is_active) == \
        ("Humedad norte", 15, (Decimal("72.50"), Decimal("88.00")), False)


def test_102_fr3b_null_empties_a_limit(client, db, account):
    a, _ = account("a@example.com")
    sensor = create(client, a).json()["id"]
    r = client.patch(f"/sensors/{sensor}", json={"min_val": None}, headers=a)
    assert (r.status_code, r.json()["min_val"], r.json()["max_val"]) == (200, None, 90.0)
    [row] = rows(db)
    assert limits(row) == (None, Decimal("90.00"))
    # one emptied, the other set: order is checked against what is left (edge case table)
    r = client.patch(f"/sensors/{sensor}", json={"max_val": None, "min_val": 95}, headers=a)
    assert (r.status_code, r.json()["min_val"], r.json()["max_val"]) == (200, 95.0, None)


def test_102_fr3c_change_leaving_lower_above_upper_rejected(client, db, account):
    a, _ = account("a@example.com")
    sensor = create(client, a).json()["id"]
    for change in ({"min_val": 95}, {"max_val": 60}, {"min_val": 91, "max_val": 90}):
        assert client.patch(f"/sensors/{sensor}", json=change, headers=a).status_code == 422, change
    [row] = rows(db)
    assert limits(row) == (Decimal("70.00"), Decimal("90.00"))


def test_102_fr3d_change_with_bad_interval_rejected(client, db, account):
    a, _ = account("a@example.com")
    sensor = create(client, a).json()["id"]
    for interval in (0, -1, 2.5, None):
        r = client.patch(f"/sensors/{sensor}", json={"reading_interval_minutes": interval}, headers=a)
        assert r.status_code == 422, interval
    [row] = rows(db)
    assert row.reading_interval_minutes == 60


def test_102_fr3e_type_unit_connection_cannot_change(client, db, account):
    a, _ = account("a@example.com")
    sensor = create(client, a).json()["id"]
    for change in ({"type": "temperature"}, {"unit": "°C"}, {"connection_type": "bluetooth"},
                   {"name": "Otro", "type": "temperature"}):  # not even alongside an allowed field
        assert client.patch(f"/sensors/{sensor}", json=change, headers=a).status_code == 422, change
    [row] = rows(db)
    assert (row.name, row.type, row.unit, row.connection_type) == ("Humedad invernadero 1", "humidity", "%", "wifi")


def test_102_fr3f_other_users_or_missing_sensor_not_found(client, db, account):
    a, _ = account("a@example.com")
    b, _ = account("b@example.com")
    theirs = create(client, b).json()["id"]
    for sensor in (theirs, theirs + 1000):
        r = client.patch(f"/sensors/{sensor}", json={"is_active": False}, headers=a)
        assert (r.status_code, r.json()["detail"]) == (404, NOT_FOUND), sensor
    [row] = rows(db)
    assert row.is_active is True


def test_102_fr3_null_name_state_or_bad_name_rejected(client, db, account):
    a, _ = account("a@example.com")
    sensor = create(client, a).json()["id"]
    for change in ({"name": None}, {"is_active": None}, {"name": ""}, {"name": "x" * 101}):
        assert client.patch(f"/sensors/{sensor}", json=change, headers=a).status_code == 422, change
    [row] = rows(db)
    assert (row.name, row.is_active) == ("Humedad invernadero 1", True)


# FR-4 — Regenerar la clave

def test_102_fr4a_new_key_replaces_stored_hash(client, db, account):
    a, _ = account("a@example.com")
    created = create(client, a).json()
    old_hash = rows(db)[0].ingest_key_hash
    assert client.post(f"/sensors/{created['id']}/ingest-key", headers=a).status_code == 200
    [row] = rows(db)
    assert row.ingest_key_hash not in (old_hash, sha256(created["ingest_key"]))


def test_102_fr4b_new_key_answered_once_and_matches_hash(client, db, account):
    a, _ = account("a@example.com")
    created = create(client, a).json()
    body = client.post(f"/sensors/{created['id']}/ingest-key", headers=a).json()
    assert set(body) == {"ingest_key"}
    assert body["ingest_key"] != created["ingest_key"]
    assert rows(db)[0].ingest_key_hash == sha256(body["ingest_key"])


def test_102_fr4c_other_users_or_missing_sensor_not_found(client, db, account):
    a, _ = account("a@example.com")
    b, _ = account("b@example.com")
    theirs = create(client, b).json()["id"]
    before = rows(db)[0].ingest_key_hash
    for sensor in (theirs, theirs + 1000):
        r = client.post(f"/sensors/{sensor}/ingest-key", headers=a)
        assert (r.status_code, r.json()["detail"]) == (404, NOT_FOUND), sensor
    assert rows(db)[0].ingest_key_hash == before


# NFR Security: every route needs a token

def test_102_security_routes_need_token(client):
    for method, path in (("POST", "/sensors"), ("GET", "/sensors"), ("GET", "/sensors/1"),
                         ("PATCH", "/sensors/1"), ("POST", "/sensors/1/ingest-key")):
        assert client.request(method, path, json={}).status_code == 401, (method, path)
