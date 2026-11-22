# 001 — Cuentas y autenticación · Tasks

Status: as-built · Spec: `spec.md` · Plan: `plan.md`

`[x]` = existe en el código hoy (aunque no corra de punta a punta: ver §C). `[ ]` = por hacer.
Las tareas de §A reconstruyen el orden de construcción; §C es lo que falta o está roto. No hay pruebas
todavía: *Made when* de §A dice cómo inspeccionarlo hoy. 002 T05 trae la base de pruebas, que T14 usa.

## A. Backend
- [x] **T01 — Modelo de cuenta** · FR-1.a, FR-1.e
  `app/models.py`: tabla `users` con correo único e indexado y `password_hash`.
  *Made when:* `grep -n "class User" app/models.py` y `grep -n "unique=True" app/models.py` apuntan a `email`. Sin prueba.
- [x] **T02 — Esquemas de cuenta y token** · FR-1.b, FR-1.c, FR-2.a
  `app/schemas.py`: `UserCreate`, `UserOut` (sin contraseña), `Token`.
  *Made when:* `.venv/bin/python -c "from app.schemas import UserOut; print(list(UserOut.model_fields))"` imprime `['id', 'name', 'email', 'created_at']`. Sin prueba.
- [x] **T03 — Hash de contraseñas** · FR-1.d, FR-2.c, FR-2.d · after T01
  `app/routers/auth.py`: `get_password_hash` y `verify_password` sobre bcrypt.
  *Made when:* `grep -n "bcrypt" app/routers/auth.py`. No se puede ejecutar hasta T08/T09. Sin prueba.
- [x] **T04 — Emisión y validación del token** · FR-2.b, FR-3.a, FR-3.c, FR-3.d · after T01
  `app/deps.py`: `create_access_token` y `get_current_user`.
  *Made when:* `grep -n "def get_current_user" app/deps.py`. No importa hasta T08. Sin prueba.
- [x] **T05 — Registro** · FR-1.a, FR-1.b, FR-1.e · after T02, T03
  `app/routers/auth.py`: `register` (400 si el correo existe).
  *Made when:* `grep -n "El email ya está registrado" app/routers/auth.py`. No alcanzable hasta T09, T10. Sin prueba.
- [x] **T06 — Inicio de sesión** · FR-2.a, FR-2.c, FR-2.d · after T03, T04
  `app/routers/auth.py`: `login` con formulario OAuth2 y un solo mensaje de fallo.
  *Made when:* `grep -n "Email o contraseña incorrectos" app/routers/auth.py`. Sin prueba.

— checkpoint: el código de FR-1 a FR-3 está escrito; todavía no se puede arrancar (ver §C) —

## B. Tests, migrations and tooling
Nada construido (no hay `tests/`). Ver T14.

## C. What could change
- [x] **T07 — Base de pruebas disponible** · — · after 002 T05
  Esperar la base de pruebas de 002 (pytest, base separada). Sin código propio.
  *Made when:* `.venv/bin/python -m pytest tests -q` corre con la prueba de 002 T06.
- [x] **T08 — Crear el módulo de configuración** · FR-2.b, FR-3.a, FR-3.c
  `app/config.py`: `get_settings()` con caché que lee `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` del entorno (plan D4). Sin valor por defecto para la clave.
  *Made when:* `.venv/bin/python -c "from app.deps import settings; print(bool(settings.SECRET_KEY))"` imprime `True`.
- [x] **T09 — Quitar el listado de cuentas y arreglar el import de auth** · reglas 1 y 2
  `app/routers/auth.py`: borrar `GET /users` (usa `app` y `select` sin definir y lista todas las cuentas sin autenticar).
  *Made when:* `grep -n "/users" app/routers/auth.py` no devuelve nada y `.venv/bin/python -c "import app.routers.auth"` termina sin error.
- [x] **T10 — Montar el router de auth** · FR-1.a, FR-2.a · after T08, T09
  `app/main.py`: `app.include_router(auth.router)`.
  *Made when:* `uvicorn app.main:app` y `curl -s localhost:8000/openapi.json` listan `/auth/register` y `/auth/login`.
- [x] **T11 — Validar el correo** · FR-1.f
  `requirements.txt`: añadir `email-validator`; `app/schemas.py`: importar `EmailStr`/`Optional` y usar `EmailStr` en `UserCreate`; borrar `UserLogin` y `TokenData` sin uso (cierra la parte de nombres sin importar de T13).
  *Made when:* `.venv/bin/python -m pytest tests -k "001 and fr1f" -q` pasa.
- [x] **T12 — Correo único sin distinguir mayúsculas y a prueba de carrera** · FR-1.e, FR-1.g · after T10
  `app/routers/auth.py`: normalizar el correo a minúsculas al registrar, al buscar y en `login`; atrapar `IntegrityError` en el commit y responder con el mensaje de FR-1.e.
  *Made when:* `.venv/bin/python -m pytest tests -k "001 and (fr1e or fr1g)" -q` pasa, incluido un registro duplicado simultáneo.
- [x] **T13 — Quitar restos** · —
  `app/main.py`: borrar `pwd_context` y los imports sin uso; `app/deps.py`: reemplazar `datetime.utcnow()` (obsoleto) por `datetime.now(timezone.utc)`.
  *Made when:* `grep -nE "pwd_context|CryptContext|utcnow" app/main.py app/deps.py` no devuelve nada.
- [x] **T14 — Pruebas de FR-1 a FR-3** · FR-1.a, FR-1.b, FR-1.c, FR-1.d, FR-1.e, FR-1.f, FR-1.g, FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-3.a, FR-3.b, FR-3.c, FR-3.d · after T07, T10
  `tests/test_001_accounts_auth.py`: las 15 filas de plan §5; las de T11/T12 nacen en rojo y se ponen en verde con esas tareas.
  *Made when:* `.venv/bin/python -m pytest tests -k 001 -q` pasa y `python3 .claude/skills/sdd/scripts/sdd_check.py specs/001-accounts-auth` no lista bullets sin prueba.

- [x] **T15 — Ver mi cuenta** · FR-4.a · after T10
  `app/routers/auth.py`: `GET /auth/me` con `get_current_user`, responde `UserOut`.
  *Made when:* `.venv/bin/python -m pytest tests -k "001 and fr4" -q` pasa.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T01, T02, T03, T05, T10, T11, T12, T14 |
| FR-2 | T02, T03, T04, T06, T08, T10, T14 |
| FR-3 | T04, T08, T14 |
| FR-4 | T15 |

## E. The gates

CI: ninguna definida (no hay workflow en el repo). Locales, tal como el perfil:
`.venv/bin/python -c "import app.main"` y `.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-13 · — · spec as-built escrito a partir del árbol de trabajo · ningún task de §C hecho.
- 2026-11-16 · base · `8622093` · árbol sucio (cambios previos sin confirmar en `.gitignore`, `deps.py`, `routers/auth.py`, `schemas.py`).
- 2026-11-16 · T08 · done · `app/config.py` (pydantic-settings, `hide_input_in_errors` para no volcar ajustes en un error); `SECRET_KEY` añadido a `.env` por la persona dueña.
- 2026-11-16 · T09 · done · `GET /users` borrado; el import necesitaba también los esquemas de T11.
- 2026-11-16 · T10 · done · uvicorn + `/openapi.json` listan `/auth/register` y `/auth/login`.
- 2026-11-16 · T13 · done · también cumple 002 T10.
- 2026-11-16 · T11 · blocked · código hecho (`EmailStr`, `email-validator==2.4.0`, `UserLogin`/`TokenData` borrados); sin ver en verde: la base de pruebas niega permisos (ver T14).
- 2026-11-16 · T12 · blocked · código hecho (minúsculas en registro y login, `IntegrityError` → 400); sin ver en verde. Además `get_current_user` rechaza un `sub` no numérico con 401 (spec §6), cubierto en `test_001_fr3c`.
- 2026-11-16 · T14 · blocked · `tests/test_001_accounts_auth.py` con las 15 filas de plan §5 (+ carrera FR-1.e, `sub` no numérico en FR-3.c). Falla dos veces igual: `permission denied for table users`: las tablas de `TEST_DB_NAME` pertenecen a otro rol que el de `DB_USER`. Espera a que la persona dueña las borre o les cambie el dueño.
- 2026-11-16 · T07 · done · 002 T05 en verde tras corregir la persona dueña los permisos de la base de pruebas.
- 2026-11-16 · T11 · done · `pytest -k "001 and fr1f"` pasa.
- 2026-11-16 · T12 · done · `pytest -k "001 and (fr1e or fr1g)"` pasa, incluida la carrera.
- 2026-11-16 · T14 · done · 16 pruebas de 001 en verde; `sdd_check` sin bullets sin prueba.
- 2026-11-16 · round 1 · T07–T14 · gates green (import + 17 passed; warnings solo de starlette/anyio en Python 3.14) · floor: sin pruebas borradas, saltadas ni supresiones.
- 2026-11-19 · T15 · done · 2 pruebas fr4a (fallaron con 404: sin ruta) · `GET /auth/me` → `UserOut`; sin token o token inválido → 401 por FR-3; pedido por la sesión del frontend (D6).
