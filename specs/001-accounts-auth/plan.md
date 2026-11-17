# 001 — Cuentas y autenticación · Implementation plan

Status: as-built · Spec: `spec.md` · Reference: `specs/sdd.profile.md`

Describe cómo está construido hoy (árbol de trabajo, con cambios sin confirmar en `deps.py`,
`routers/auth.py` y `schemas.py`). Donde el código no cumple el spec, la fila lo dice y remite a
tasks §C.

## 1. Module structure

### A. Backend (`app/`)
| File | Holds | FR |
|---|---|---|
| `app/models.py` | tabla `users` (modelo `User`) | FR-1.a, FR-1.e |
| `app/schemas.py` | `UserCreate`, `UserOut`, `Token`; sobran `UserLogin`, `TokenData` (sin uso) | FR-1.b, FR-1.c, FR-1.f, FR-2.a |
| `app/routers/auth.py` | `register`, `login`, `get_password_hash`, `verify_password`, contexto de hash; contiene además un `GET /users` roto | FR-1, FR-2.a, FR-2.c, FR-2.d |
| `app/deps.py` | `create_access_token`, `get_current_user` (esquema OAuth2 bearer) | FR-2.b, FR-3 |
| `app/config.py` | **no existe**; `deps.py` espera `get_settings()` con `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | FR-2.b, FR-3 |
| `app/main.py` | no monta el router de auth | FR-1, FR-2 |

### B. Tests, migrations and tooling
No toca nada todavía: no hay `tests/`. Lo añade 002 (T05) y 001 T14.

## 2. Data model

Tabla `users` (existe):

| Campo | Tipo | Null | Restricción |
|---|---|---|---|
| `id` | BigInteger | no | PK, autoincremental |
| `name` | String(100) | no | |
| `email` | String(150) | no | único, indexado (hoy distingue mayúsculas) |
| `password_hash` | String(255) | no | hash bcrypt con sal |
| `created_at` | DateTime con zona | sí | `now()` del servidor |

Representación de la API (`UserOut`; nunca incluye `password_hash`):

```json
{ "id": 7, "name": "Ana Pérez", "email": "ana@example.com", "created_at": "2026-11-13T04:12:09.481Z" }
```

Token (`Token`) y cuerpos de error:

```json
{ "access_token": "<jwt>", "token_type": "bearer" }
{ "detail": "El email ya está registrado" }
{ "detail": "Email o contraseña incorrectos" }
{ "detail": "No se pudo validar las credenciales" }
```

Carga del token: `{"sub": "<id de cuenta como texto>", "exp": <vencimiento>}`.

## 3. Surface

| Método y ruta | Autenticación | Filtro por dueño | Respuestas | FR |
|---|---|---|---|---|
| `POST /auth/register` (JSON: `name`, `email`, `password`) | pública | n/a | 201 `UserOut`; 400 correo repetido; 422 cuerpo inválido | FR-1 |
| `POST /auth/login` (formulario: `username`=correo, `password`) | pública | n/a | 200 `Token`; 401 con `WWW-Authenticate: Bearer` | FR-2 |
| dependencia `get_current_user` | la usan 101–104 | entrega la cuenta | 401 "No se pudo validar las credenciales" | FR-3 |
| `GET /users` (en `routers/auth.py`) | ninguna | ninguna | no carga; **se elimina** (T09) | — |

Sin pantallas: es una API.

## 4. Technical decisions

**D1 — JWT firmado (HS, clave y algoritmo de la configuración), `sub` = id como texto, `exp` obligatorio.** *Discarded:* sesiones en servidor (necesitan almacén y no hacen falta con una instancia; ver spec D1). (FR-2.b, FR-3)

**D2 — `passlib` con `bcrypt` (`CryptContext(schemes=["bcrypt"], deprecated="auto")`).** *Discarded:* `hashlib` manual con sal (reinventa lo que ya está instalado). (FR-1.d)

**D3 — El inicio de sesión recibe el formulario estándar OAuth2** (`username` = correo) para que el botón "Authorize" de `/docs` funcione. *Discarded:* cuerpo JSON con `UserLogin` (existe pero nadie lo usa). (FR-2.a)

**D4 — La configuración vive en `app/config.py` con `pydantic-settings` (`get_settings()` con caché).** `deps.py` ya la importa y `pydantic-settings` está instalado. *Discarded:* `os.getenv` suelto como en `database.py` (repite nombres y valores por defecto en cada módulo). Desde 002 T09 también lee los ajustes de la base, y un `SECRET_KEY` vacío cuenta como ausente (002 plan D3). (FR-2.b, FR-3)

**D5 — Unicidad del correo sin distinguir mayúsculas: se normaliza a minúsculas al guardar y al buscar, y un índice único protege la carrera** (el commit atrapa `IntegrityError` y responde el mismo mensaje). *Discarded:* `lower(email)` solo en la consulta (no cierra la carrera); tipo `citext` (extensión de Postgres que ata el modelo a ella). Normalizar al guardar cambia datos existentes, pero la aplicación no puede registrar cuentas hoy, así que no hay cuentas que migrar. (FR-1.e, FR-1.g)

**D6 — Validación de correo con `EmailStr` (paquete `email-validator` en `requirements.txt`).** *Discarded:* expresión regular propia. (FR-1.f)

**D7 — Códigos como están hoy:** 400 correo repetido, 401 credenciales. Ver spec D4. (FR-1.e)

## 5. Test strategy

Pruebas en `tests/test_001_accounts_auth.py`, con `TestClient` y la base de pruebas de 002 (D4 de 002);
nombres `test_001_fr1a_…` (ears.md). Los tokens vencidos se fabrican con
`create_access_token(..., expires_delta=timedelta(seconds=-1))`; el de otra clave, con `jwt.encode`.

| Bullet | Caso (Given / When / Then) | Kind |
|---|---|---|
| FR-1.a | Given ningún correo registrado / When se envía nombre, correo y contraseña / Then existe una cuenta con ese correo | event |
| FR-1.b | Given el registro anterior / When se lee la respuesta / Then trae id, nombre, correo, fecha de creación | event |
| FR-1.c | Given una cuenta creada / When se registra y se inicia sesión / Then ninguna respuesta contiene `password` ni `password_hash` | positive |
| FR-1.d | Given una cuenta creada / When se lee la fila / Then `password_hash` no es la contraseña y `verify_password` la acepta | positive |
| FR-1.e | Given el correo ya registrado / When se registra otra vez / Then 400 con "El email ya está registrado" y sigue habiendo una cuenta | negative |
| FR-1.f | Given un correo "no-es-correo" / When se registra / Then 422 y no hay cuenta | negative |
| FR-1.g | Given "ana@example.com" registrado / When se registra "Ana@Example.com" / Then 400 con el mismo mensaje | negative |
| FR-2.a | Given una cuenta / When se inicia sesión con sus datos / Then `token_type` es "bearer" y hay `access_token` | event |
| FR-2.b | Given un token emitido / When se decodifica / Then lleva el id de la cuenta y un `exp` igual a ahora + minutos configurados (±5 s) | positive |
| FR-2.c | Given ninguna cuenta / When se inicia sesión con un correo cualquiera / Then 401 "Email o contraseña incorrectos" | negative |
| FR-2.d | Given una cuenta / When se inicia sesión con otra contraseña / Then 401 con el mismo cuerpo que FR-2.c | negative |
| FR-3.a | Given un token vigente / When se llama a una ruta de prueba protegida / Then responde con la cuenta del token | event |
| FR-3.b | Given ninguna cabecera / When se llama a la ruta / Then 401 | negative |
| FR-3.c | Given token vencido, token con otra clave, texto basura y token sin `sub` / When se llama / Then 401 "No se pudo validar las credenciales" cada vez | negative |
| FR-3.d | Given un token de una cuenta borrada de la base / When se llama / Then 401 con el mismo mensaje | negative |

## 6. Build order

1. Configuración (`app/config.py`) — hoy falta.
2. Modelo `User` (existe, 002).
3. Esquemas `UserCreate`, `UserOut`, `Token`.
4. `create_access_token` y `get_current_user` en `deps.py`.
5. `register` y `login` en `routers/auth.py` con las funciones de hash.
6. Montar el router en `main.py`.
7. Pruebas (T14).

## 7. Requirement coverage

| FR | Plan sections |
|---|---|
| FR-1 | §1, §2, §3, §4 D2 D5 D6 D7, §5 |
| FR-2 | §1, §2, §3, §4 D1 D3 D4, §5 |
| FR-3 | §1, §2, §3, §4 D1 D4, §5 |
