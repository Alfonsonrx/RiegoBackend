# 002 — Base de datos y fundamentos · Tasks

Status: as-built · Spec: `spec.md` · Plan: `plan.md`

`[x]` = existe en el código hoy; `[ ]` = por hacer. Sin pruebas todavía: *Made when* de §A dice cómo
inspeccionarlo hoy. T05 es la base de pruebas que usan 001 y 101–104.

## A. Backend
- [x] **T01 — Conexión desde el entorno** · FR-1.a, FR-3.a
  `app/database.py`: motor PostgreSQL, `SessionLocal`, `get_db`.
  *Made when:* `grep -n "def get_db" app/database.py`. Sin prueba.
- [x] **T02 — Las cinco tablas** · FR-1.b · after T01
  `app/models.py`: `users`, `notifications`, `sensors`, `sensor_readings`, `irrigation_schedule`.
  *Made when:* `.venv/bin/python -c "from app.models import Base; print(sorted(Base.metadata.tables))"` imprime las cinco. Sin prueba.
- [x] **T03 — Estructura al arrancar** · FR-1.b, FR-1.c · after T02 · (reemplazada por Alembic en T07–T08)
  `app/main.py`: `Base.metadata.create_all(engine)` al importar.
  *Made when:* `grep -n "create_all" app/main.py`; arrancar con la base arriba la deja con las cinco tablas. Sin prueba.
- [x] **T04 — Consulta de estado** · FR-2.a, FR-2.b, FR-2.c · after T01
  `app/main.py`: `GET /db-check` con `SELECT 1`.
  *Made when:* `uvicorn app.main:app` y `curl -s localhost:8000/db-check` imprime `{"db":"ok"}`. Sin prueba.

— checkpoint: el almacén y la consulta de estado funcionan con la base arriba —

## B. Tests, migrations and tooling
Nada construido todavía. Ver T05–T09 en §C.

## C. What could change
- [x] **T05 — Base de pruebas** · —
  `requirements.txt`: añadir `pytest` con versión fija; `tests/conftest.py`: base `TEST_DB_NAME` (plan D4), `TRUNCATE … RESTART IDENTITY CASCADE` entre pruebas, `get_db` reemplazado, `TestClient`.
  *Made when:* `.venv/bin/python -m pytest tests -q` descubre `conftest.py` y ejecuta una prueba trivial contra la base de pruebas.
- [x] **T06 — Pruebas de FR-1 a FR-3** · FR-1.a, FR-1.b, FR-1.c, FR-2.a, FR-2.b, FR-2.c, FR-3.a · after T05
  `tests/test_002_database_foundation.py`: las 7 filas de plan §5.
  *Made when:* `.venv/bin/python -m pytest tests -k 002 -q` pasa y `python3 .claude/skills/sdd/scripts/sdd_check.py specs/002-database-foundation` no lista bullets sin prueba.
- [x] **T07 — Alembic con migración base** · FR-1.b · after T06
  `migrations/` (`alembic init`), `env.py` apuntando a `Base.metadata` y a las variables de conexión; revisión base con las cinco tablas.
  *Made when:* `alembic upgrade head` sobre una base vacía crea las cinco tablas y `alembic current` muestra la revisión.
- [x] **T08 — Quitar `create_all` del arranque** · FR-1.b, FR-1.c, FR-1.d · after T07
  `app/main.py`: borrar `create_all`; documentar `alembic upgrade head` en `README.md`; la base de pruebas pasa a crear la estructura con Alembic o con `create_all` explícito en `conftest.py`.
  *Made when:* `grep -n "create_all" app/main.py` no devuelve nada, `.venv/bin/python -c "import app.main"` no abre conexión y `pytest -k 002` sigue verde.
- [x] **T09 — Credenciales fuera del código** · FR-3.a
  `app/database.py`: sin valores por defecto para `DB_USER` y `DB_PW` (falla con un mensaje que nombra el ajuste); `.env.example`: solo los nombres `DB_USER`, `DB_PW`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `TEST_DB_NAME`, sin valores reales.
  *Made when:* `grep -nE "postgres" app/database.py` no encuentra un valor por defecto de usuario ni de contraseña y `pytest -k "002 and fr3a"` pasa.
- [x] **T10 — Quitar restos de `main.py`** · —
  `app/main.py`: borrar `pwd_context`, `CryptContext` y las importaciones sin uso (`HTTPException`, `select`, `IntegrityError`, `schemas`).
  *Made when:* `grep -nE "pwd_context|CryptContext|IntegrityError" app/main.py` no devuelve nada y `.venv/bin/python -c "import app.main"` sigue funcionando.
- [ ] **T11 — Seguimiento: tablas sin uso** · —
  Sensores, lecturas, calendario y notificaciones los terminan 101–104; los módulos de rutas vacíos se llenan o se borran ahí.
  *Made when:* `wc -c app/routers/*.py` no muestra ningún archivo vacío.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T01, T02, T03, T06, T07, T08 |
| FR-2 | T04, T06 |
| FR-3 | T01, T06, T09 |

## E. The gates

CI: ninguna definida (no hay workflow). Locales: `.venv/bin/python -c "import app.main"` y
`.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-13 · — · spec as-built escrito a partir del árbol de trabajo · ningún task de §C hecho.
- 2026-11-16 · T05 · blocked · `pytest==9.2.0` fijado; `tests/conftest.py` apunta `DB_NAME` a `TEST_DB_NAME` antes de importar la app (en vez de reemplazar `get_db`: mismo efecto, también cubre `create_all`), se niega a correr si `TEST_DB_NAME` es la base real, `TRUNCATE … RESTART IDENTITY CASCADE` tras cada prueba; prueba trivial `test_002_runs_against_test_database`. Bloqueada: el rol de la app no tiene permisos sobre las tablas de la base de pruebas.
- 2026-11-16 · T10 · done · hecho por 001 T13.
- 2026-11-16 · T05 · done · permisos corregidos; `pytest tests -q` corre la prueba trivial contra la base de pruebas.
- 2026-11-16 · base · `667fa17` · árbol limpio.
- 2026-11-16 · T06 · done · 6 pruebas nuevas (FR-1.a/b/c, FR-2.a+c, FR-2.b, FR-3.a); el "arranque" vuelve a ejecutar `app.database`/`app.main` en un módulo nuevo sin tocar `sys.modules`; FR-1.b borra y recrea las tablas solo en la base de pruebas. Código previo a las pruebas (as-built): verificadas con mutación (sin `create_all` → falla FR-1.b; sin `SELECT 1` → falla FR-2.b), `main.py` restaurado. Suite completa: 23 passed.
- 2026-11-16 · T07 · done · `alembic.ini` (sin URL: la conexión sale de `app/database.py`), `migrations/env.py` con el `engine` y `Base.metadata` de la app, revisión `e4010b5a1ecb` autogenerada contra la base de pruebas vacía. Sobre la base de pruebas: `upgrade head` crea las cinco tablas, `current` = `e4010b5a1ecb (head)`, `alembic check` sin diferencias, `downgrade base` las borra; base de pruebas dejada vacía. `alembic.ini` en la raíz no figura en las rutas del área B del perfil (lo exige `alembic init`). La base real no se tocó: ya tiene las tablas de `create_all`, necesita `alembic stamp head` una vez. Suite: 23 passed.
- 2026-11-16 · T07 · rehecho · la base real no venía de `create_all` sino de un script a mano (FK en cascada, seis índices `idx_*`, `created_at` no nulo, `UNIQUE (email)`, defaults en la base) y la persona dueña ya la había marcado en `e4010b5a1ecb`. `models.py` ajustado a ella (spec D5) y revisión regenerada con el mismo id. Base real (solo lectura): `compare_metadata` con defaults → sin diferencias. Base de pruebas: `upgrade head`, `check` sin diferencias, `downgrade base`, dejada vacía. Suite: 23 passed.
- 2026-11-16 · T08 · done · `create_all` fuera de `main.py` (importar abre 0 conexiones); `conftest.py` reconstruye la base de pruebas con `alembic upgrade head` al empezar; FR-1.b/c reescritas a "WHEN se aplican las migraciones" y FR-1.d nueva (spec D6, aprobado por la persona dueña); pruebas FR-1.b (bajar a `base`, subir, cero diferencias con los modelos), FR-1.c (subir de nuevo conserva la cuenta), FR-1.d (arrancar no crea tablas). Mutación: `create_all` repuesto → falla FR-1.d; índice quitado de la migración → falla FR-1.b; ambos restaurados. `alembic.ini` con `%(here)s` (funciona desde cualquier carpeta); `env.py` ya no desactiva los loggers de la app. README: instalación, migraciones, cambiar el esquema, pruebas.
- 2026-11-16 · — · la persona dueña confirmó T06–T08 como `0255254`.
- 2026-11-16 · T09 · done · ajustes `DB_*` movidos a `config.py` (plan D3): `DB_USER`/`DB_PW` sin valor por defecto, vacío = ausente (`env_ignore_empty`, cubre también un `SECRET_KEY` vacío), `.env` por ruta absoluta; `database.py` sin `os.getenv` ni `load_dotenv`. Prueba nueva `test_002_fr3a_no_default_credentials` (sin `.env`: `DB_USER` sin definir y `DB_PW` vacío fallan nombrando el ajuste, sin valores secretos en el mensaje). Mutación: `DB_USER` con valor por defecto → falla; sin `env_ignore_empty` → falla; restaurado. *Made when:* el único "postgres" en `database.py` es el driver `postgresql+psycopg2`. `.env.example`: secretos vacíos y valores de desarrollo no secretos (localhost, 5432, nombres de base, HS256, 30) en vez de solo nombres. Suite: 25 passed; `alembic current` sobre la base real sigue en `e4010b5a1ecb (head)`.
