# 002 — Base de datos y fundamentos · Implementation plan

Status: as-built · Spec: `spec.md` · Reference: `specs/sdd.profile.md`

## 1. Module structure

### A. Backend (`app/`)
| File | Holds | FR |
|---|---|---|
| `app/config.py` | ajustes `DB_*` junto a los de token (T09); usuario y contraseña sin valor por defecto | FR-3.a |
| `app/database.py` | `engine` desde `get_settings()` (PostgreSQL vía `psycopg2`, `pool_pre_ping`), `SessionLocal`, dependencia `get_db` (una sesión por petición, siempre cerrada) | FR-1.a, FR-3.a |
| `app/models.py` | `Base` y las cinco tablas: `users`, `notifications`, `sensors`, `sensor_readings`, `irrigation_schedule` | FR-1.a, FR-1.b |
| `app/main.py` | aplicación FastAPI y `GET /db-check`; no toca la estructura (T08) | FR-1.d, FR-2 |

### B. Tests, migrations and tooling
| File | Holds | FR |
|---|---|---|
| `requirements.txt` | dependencias fijas, incluido `pytest` (T05) | — |
| `tests/conftest.py` | base de pruebas reconstruida desde las migraciones al empezar (T08), `TestClient`, sesión de prueba (T05) | todos |
| `tests/test_002_database_foundation.py` | las pruebas de plan §5 (T06) | FR-1, FR-2, FR-3 |
| `alembic.ini`, `migrations/env.py` | Alembic; la conexión sale de `app/database.py`, el esquema de `Base.metadata` (T07) | FR-1.b, FR-1.c |
| `README.md` | instalación, `alembic upgrade head`, cómo cambiar el esquema (T08) | FR-1.b |
| `migrations/versions/e4010b5a1ecb_base_five_tables.py` | revisión base: las cinco tablas de §2 (T07) | FR-1.b |
| `.env.example` | solo nombres de ajustes (T09) | FR-3.a |

## 2. Data model

Las cinco tablas hoy, iguales en la base real, en `models.py` y en la revisión base `e4010b5a1ecb` (spec D5;
la forma de las cuatro sin uso la consumen 101–104 y puede cambiar ahí). Toda FK borra en cascada; los
valores por defecto los pone la base.

| Tabla | Campo | Tipo | Null | Restricción |
|---|---|---|---|---|
| `users` | `id` | BigInteger | no | PK, autoincremental |
| | `name` | String(100) | no | |
| | `email` | String(150) | no | único (restricción `users_email_key`) |
| | `password_hash` | String(255) | no | |
| | `created_at` | DateTime con zona | no | `now()` |
| `notifications` | `id` | BigInteger | no | PK |
| | `user_id` | BigInteger | no | FK → `users.id` en cascada; índice `idx_notifications_user_id` |
| | `type` | String(30) | no | |
| | `message` | Text | no | |
| | `is_read` | Boolean | no | `false` |
| | `created_at` | DateTime con zona | no | `now()` |
| `sensors` | `id` | BigInteger | no | PK |
| | `created_by` | BigInteger | no | FK → `users.id` en cascada; índice `idx_sensors_created_by` |
| | `name` | String(100) | no | |
| | `type`, `unit`, `connection_type` | String(20) | no | |
| | `min_val`, `max_val` | Numeric(5,2) | sí | |
| | `reading_interval_minutes` | Integer | no | |
| | `is_active` | Boolean | no | `true` |
| `sensor_readings` | `id` | BigInteger | no | PK |
| | `sensor_id` | BigInteger | no | FK → `sensors.id` en cascada; índice `idx_sensor_readings_sensor_id` |
| | `value` | Numeric(5,2) | no | |
| | `recorded_at` | DateTime con zona | no | `now()`; índice `idx_sensor_readings_recorded_at` |
| `irrigation_schedule` | `id` | BigInteger | no | PK |
| | `created_by` | BigInteger | no | FK → `users.id` en cascada; índice `idx_irrigation_schedule_created_by` |
| | `irrigation_date` | Date | no | índice `idx_irrigation_schedule_date` |
| | `irrigation_time` | Time | no | sin zona (101 D4) |
| | `is_active` | Boolean | no | `true` |

Respuesta de la consulta de estado:

```json
{ "db": "ok" }
```

## 3. Surface

| Método y ruta | Autenticación | Filtro por dueño | Respuestas | FR |
|---|---|---|---|---|
| `GET /db-check` | pública (regla 2) | n/a | 200 `{"db": "ok"}`; con la base caída, error de servidor (500) | FR-2 |

Ajustes de la base que lee `config.py` (nombres, nunca valores; lista completa en `.env.example`): `DB_USER`, `DB_PW`, `DB_HOST`,
`DB_PORT`, `DB_NAME`. FR-3.

## 4. Technical decisions

**D1 — SQLAlchemy 2 síncrono con `psycopg2` y una sesión por petición (`get_db`); la base es PostgreSQL (el comentario de `requirements.txt` apunta a Supabase).** *Discarded:* SQLAlchemy asíncrono (ningún requisito de concurrencia lo justifica en un prototipo). (FR-1.a)

**D2 — Estructura creada y cambiada solo por Alembic (`alembic upgrade head`), nunca al arrancar (spec D6); la revisión base reproduce la base real (spec D5).** Las pruebas reconstruyen su base desde las migraciones al comienzo de cada corrida, así que una migración que no coincide con los modelos rompe las pruebas (FR-1.b compara modelos y base como `alembic check`). *Discarded:* `create_all` al importar (como estaba hasta T08: una base nueva quedaba sin versión y una tabla existente nunca recibía columnas); migrar al arrancar (permisos para cambiar la estructura y carreras entre instancias); `create_all` en las pruebas (no probaría las migraciones). (FR-1.b, FR-1.c, FR-1.d)

**D3 — Todos los ajustes (base y token) los lee `config.py` con `pydantic-settings`, del entorno y del `.env` de la raíz (ruta absoluta, sirve desde cualquier carpeta).** `DB_USER` y `DB_PW` no tienen valor por defecto; un valor vacío cuenta como ausente (`env_ignore_empty`, así un `.env` copiado de `.env.example` sin completar falla en vez de conectar con "" o firmar tokens con una clave vacía); `hide_input_in_errors` hace que el error nombre el ajuste sin mostrar valores. *Discarded:* `os.getenv` con valores por defecto en `database.py` (como estaba hasta T09: contraseña de desarrollo en el código); dos formas de leer ajustes. (FR-3.a)

**D4 — Las pruebas usan otra base PostgreSQL (`TEST_DB_NAME`, mismo servidor y usuario del entorno) que `conftest.py` reconstruye con las migraciones al empezar y vacía con `TRUNCATE … RESTART IDENTITY CASCADE` entre pruebas; `DB_NAME` se apunta a ella antes de importar la aplicación.** *Discarded:* SQLite en memoria (la clave `BigInteger` no se autoincrementa en SQLite); transacción con rollback por prueba (las rutas hacen `commit`, exigiría savepoints). (todos los FR de 001–104)

**D5 — La consulta de estado es `SELECT 1` sin tocar tablas.** *Discarded:* contar filas (más lenta y revela datos). (FR-2.a)

## 5. Test strategy

`tests/test_002_database_foundation.py` con la base de D4. El "reinicio" de FR-1.a se simula cerrando
el motor y abriendo uno nuevo; FR-1.b–d corren Alembic en el mismo proceso (`command.upgrade`/`downgrade`); FR-3.a recarga `app.database` con variables del entorno falsas
(`monkeypatch`) y compara `engine.url` sin imprimirlo.

| Bullet | Caso (Given / When / Then) | Kind |
|---|---|---|
| FR-1.a | Given una cuenta guardada / When se descarta el motor y se abre otro / Then la cuenta sigue ahí | positive |
| FR-1.b | Given una base sin las tablas (migraciones bajadas a `base`) / When se aplican las migraciones / Then existen las cinco tablas y no difieren de los modelos | event |
| FR-1.c | Given la base al día y una cuenta / When se aplican las migraciones otra vez / Then la cuenta no cambió | event |
| FR-1.d | Given una base sin las tablas / When arranca el sistema / Then sigue sin tablas | event |
| FR-2.a | Given la base arriba / When `GET /db-check` / Then 200 `{"db": "ok"}` | event |
| FR-2.b | Given una sesión que lanza `OperationalError` / When `GET /db-check` / Then la respuesta no es 200 con `{"db": "ok"}` | negative |
| FR-2.c | Given ninguna cabecera `Authorization` / When `GET /db-check` / Then 200 | positive |
| FR-3.a | Given `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PW` con valores de prueba / When se recarga `app.database` / Then `engine.url` los usa | positive |
| FR-3.a | Given sin `.env`, `DB_USER` sin definir o `DB_PW` vacío / When se recarga `app.database` / Then falla, el error nombra el ajuste y no contiene ningún valor secreto | negative |

## 6. Build order

1. `database.py` (entorno → motor → sesión).
2. Modelos (`users` primero; el resto lo usarán 101–104).
3. `main.py`: creación de estructura y consulta de estado.
4. Base de pruebas (T05) y pruebas (T06).
5. Migraciones (T07–T08), credenciales fuera del código (T09).

## 7. Requirement coverage

| FR | Plan sections |
|---|---|
| FR-1 | §1, §2, §4 D1 D2 D4, §5 |
| FR-2 | §1, §3, §4 D5, §5 |
| FR-3 | §1, §3, §4 D3, §5 |
