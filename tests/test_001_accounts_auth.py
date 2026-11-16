from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from jose import jwt

from app import models
from app.deps import create_access_token, get_current_user, settings
from app.main import app
from app.routers.auth import verify_password

CRED = "No se pudo validar las credenciales"
BAD_LOGIN = "Email o contraseña incorrectos"
DUP = "El email ya está registrado"
ANA = {"name": "Ana Pérez", "email": "ana@example.com", "password": "orquidea-123"}


@app.get("/_test/me")  # protected route used only by the FR-3 tests
def _me(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


def register(client, **over):
    return client.post("/auth/register", json={**ANA, **over})


def login(client, email=ANA["email"], password=ANA["password"]):
    return client.post("/auth/login", data={"username": email, "password": password})


def me(client, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.get("/_test/me", headers=headers)


def count_users(db):
    return db.query(models.User).count()


# FR-1 — Registro de cuenta

def test_001_fr1a_register_creates_account(client, db):
    assert register(client).status_code == 201
    assert db.query(models.User).filter_by(email=ANA["email"]).count() == 1


def test_001_fr1b_register_returns_public_fields(client):
    body = register(client).json()
    assert set(body) == {"id", "name", "email", "created_at"}
    assert (body["name"], body["email"]) == (ANA["name"], ANA["email"])
    assert body["id"] and body["created_at"]


def test_001_fr1c_no_password_in_responses(client):
    texts = [register(client).text, login(client).text]
    for t in texts:
        assert "password" not in t and ANA["password"] not in t


def test_001_fr1d_password_stored_as_salted_hash(client, db):
    register(client)
    register(client, email="otra@example.com")  # same password, different salt
    hashes = [u.password_hash for u in db.query(models.User).all()]
    assert ANA["password"] not in hashes
    assert hashes[0] != hashes[1]
    assert all(verify_password(ANA["password"], h) for h in hashes)


def test_001_fr1e_duplicate_email_rejected(client, db):
    register(client)
    r = register(client, name="Otra")
    assert (r.status_code, r.json()["detail"]) == (400, DUP)
    assert count_users(db) == 1


def test_001_fr1e_concurrent_duplicate_rejected(client, db):
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: register(client), range(2)))
    assert sorted(r.status_code for r in results) == [201, 400]
    assert next(r for r in results if r.status_code == 400).json()["detail"] == DUP
    assert count_users(db) == 1


def test_001_fr1f_invalid_email_rejected(client, db):
    assert register(client, email="no-es-correo").status_code == 422
    assert count_users(db) == 0


def test_001_fr1g_email_case_insensitive(client, db):
    register(client)
    r = register(client, email="Ana@Example.com")
    assert (r.status_code, r.json()["detail"]) == (400, DUP)
    assert count_users(db) == 1
    assert login(client, email="ANA@example.com").status_code == 200


# FR-2 — Inicio de sesión

def test_001_fr2a_login_returns_bearer_token(client):
    register(client)
    body = login(client).json()
    assert body["token_type"] == "bearer" and body["access_token"]


def test_001_fr2b_token_identifies_account_and_expires(client):
    user_id = register(client).json()["id"]
    token = login(client).json()["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(user_id)
    expected = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assert abs(payload["exp"] - expected.timestamp()) <= 5


def test_001_fr2c_unknown_email_rejected(client):
    r = login(client, email="nadie@example.com")
    assert (r.status_code, r.json()) == (401, {"detail": BAD_LOGIN})


def test_001_fr2d_wrong_password_rejected(client):
    register(client)
    r = login(client, password="otra-clave")
    assert (r.status_code, r.json()) == (401, {"detail": BAD_LOGIN})


# FR-3 — Cuenta actual en operaciones protegidas

def test_001_fr3a_valid_token_acts_as_account(client):
    user_id = register(client).json()["id"]
    r = me(client, login(client).json()["access_token"])
    assert r.status_code == 200 and r.json()["id"] == user_id


def test_001_fr3b_missing_token_rejected(client):
    assert me(client).status_code == 401


def test_001_fr3c_bad_tokens_rejected(client):
    user_id = str(register(client).json()["id"])
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    bad = {
        "expired": create_access_token({"sub": user_id}, expires_delta=timedelta(seconds=-1)),
        "other key": jwt.encode({"sub": user_id, "exp": future}, "otra-clave", algorithm=settings.ALGORITHM),
        "garbage": "no-es-un-token",
        "no sub": create_access_token({}),
        "non-numeric sub": create_access_token({"sub": "abc"}),
    }
    for name, token in bad.items():
        r = me(client, token)
        assert (r.status_code, r.json()["detail"]) == (401, CRED), name


def test_001_fr3d_deleted_account_rejected(client, db):
    register(client)
    token = login(client).json()["access_token"]
    db.query(models.User).delete()
    db.commit()
    r = me(client, token)
    assert (r.status_code, r.json()["detail"]) == (401, CRED)
