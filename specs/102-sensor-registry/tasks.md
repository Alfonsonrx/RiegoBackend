# 102 — Registro de sensores · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Todas esperan a 001 T08 y T10, a
002 T05 y a 101 T03 (que crea `get_owned_or_404` y monta el patrón de rutas).

## A. Backend
- [x] **T01 — Columna de clave y tabla de tipos** · FR-1.b, FR-1.c, FR-1.d, FR-1.e
  `app/models.py`: `Sensor.ingest_key_hash` (String(64), único, no nulo); `app/schemas.py`: `SENSOR_TYPES`.
  *Made when:* `.venv/bin/python -c "from app.schemas import SENSOR_TYPES; print(sorted(SENSOR_TYPES))"` imprime `['humidity', 'temperature']` y `grep -n "ingest_key_hash" app/models.py` lo encuentra.
- [x] **T02 — Esquemas de sensor** · FR-1.f, FR-1.g, FR-1.h, FR-1.i, FR-1.j, FR-3.c, FR-3.d, FR-3.e · after T01
  `app/schemas.py`: `SensorCreate`, `SensorUpdate` (`extra="forbid"`), `SensorOut`, `SensorCreated`, `IngestKeyOut`.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and (fr1f or fr1g or fr1h or fr1j)" -q` pasa (los rechazos de esquema).
- [x] **T03 — Registrar un sensor** · FR-1.a, FR-1.b, FR-1.c, FR-1.d, FR-1.e, FR-1.i · after T02
  `app/routers/sensors.py`: `_new_key()`, `hash_key()` y `POST /sensors`; `app/main.py`: montar el router.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr1" -q` pasa.
- [x] **T04 — Ver mis sensores** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e · after T03
  `app/routers/sensors.py`: `GET /sensors` y `GET /sensors/{id}` con `get_owned_or_404`.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr2" -q` pasa.
- [x] **T05 — Cambiar un sensor** · FR-3.a, FR-3.b, FR-3.c, FR-3.d, FR-3.e, FR-3.f · after T04
  `app/routers/sensors.py`: `PATCH /sensors/{id}` parcial (plan D4).
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr3" -q` pasa.
- [x] **T06 — Regenerar la clave** · FR-4.a, FR-4.b, FR-4.c · after T04
  `app/routers/sensors.py`: `POST /sensors/{id}/ingest-key`.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr4" -q` pasa y la prueba de rutas sin token (NFR) devuelve 401 en las cinco rutas.

— checkpoint: sensores registrables, visibles, editables y con clave; `pytest -k 102` verde —

## B. Tests, migrations and tooling
- [x] **T07 — Migración de la clave** · FR-1.c · after T01, 002 T07
  `migrations/versions/…`: agrega `sensors.ingest_key_hash` (no nulo, único). Falla si la tabla tiene filas: vaciarla antes (plan D6).
  *Made when:* `alembic upgrade head` sobre una base con la revisión base añade la columna y `alembic downgrade -1` la quita.

## C. What could change
Nada pendiente. Otros tipos de sensor y de conexión, borrado: `specs/backlog.md`.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T01, T02, T03, T07 |
| FR-2 | T04 |
| FR-3 | T02, T05 |
| FR-4 | T06 |

## E. The gates

CI: ninguna definida. Locales: `.venv/bin/python -c "import app.main"` y `.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-13 · — · spec, plan y tasks escritos (draft) · sin tareas hechas.
- 2026-11-17 · base · `c41ba15` · árbol limpio · round 1 (modo round) T01–T06 + T07 adelantada: desde 002 T08 las pruebas construyen la base con las migraciones, así que la columna de T01 necesita su migración en el mismo paso.
- 2026-11-17 · — · ordenamiento (estructural): fixture `account` compartido en `conftest.py`; `test_101` lo usa (14 passed, sin cambio de comportamiento).
- 2026-11-17 · T01 · done · `Sensor.ingest_key_hash` (String(64), único, no nulo); `SENSOR_TYPES` en `schemas.py`. *Made when* ok.
- 2026-11-17 · T07 · done · revisión `243c35ebd9fa` autogenerada; restricción única nombrada `sensors_ingest_key_hash_key` (autogenerate la dejaba sin nombre y `downgrade` no podía borrarla). Base de pruebas: `upgrade head`, `check` sin diferencias, `downgrade -1`, `upgrade head`. La tabla `sensors` real está vacía (consulta de solo lectura): la migración aplica.
- 2026-11-17 · T02 · done · esquemas con `Literal` de tipos (derivado de `SENSOR_TYPES`) y conexiones, `Decimal(5,2)` para límites, intervalo 1..2³¹−1 (la columna es Integer), nombre 1..100 (String(100)); límites salen como número. Su *Made when* pasa por la ruta, así que se comprobó tras T03.
- 2026-11-17 · T03 · done · `POST /sensors`, `new_key()`/`hash_key()`, `check_limits()` (defaults del tipo y orden, 422 "El límite inferior no puede ser mayor que el superior"; en la ruta, no en el esquema como decía plan D3, para que crear y cambiar compartan regla y mensaje); router montado. 27 pruebas escritas antes del código (27 rojas); FR-1: 11 verdes.
- 2026-11-17 · T04 · done · `GET /sensors` (por id) y `GET /sensors/{id}` con `get_owned_or_404`; rojo: 5. Su *Made when* incluye FR-2.c, cuyo caso también mira la respuesta del `PATCH`: verde tras T05.
- 2026-11-17 · T05 · done · `PATCH /sensors/{id}` parcial; orden de límites con lo enviado mezclado con lo guardado; `extra="forbid"` rechaza tipo, unidad y conexión. Rojo: 7.
- 2026-11-17 · T06 · done · `POST /sensors/{id}/ingest-key` reemplaza el hash; rojo: 4 (incluida la de rutas sin token: la ruta no existía, 404). *Made when* ok; sin token → 401 en las cinco rutas.
- 2026-11-17 · round 1 · T01–T07 (T07 adelantada) · gates green (import + 66 passed) · floor: sin pruebas borradas (las 12 "borradas" del diff son firmas de `test_101` que ganaron `account`; siguen 14), sin aserciones quitadas, sin supresiones · revisión: id enorme → 404, `PATCH {}` → 200, ambos límites vacíos ok; propuestas (k) en FR-1, (g) en FR-3 y tope del intervalo (§10); `check_limits` en la ruta (plan D3 actualizado); nombre largo en el registro de 001 → 500 → backlog.
