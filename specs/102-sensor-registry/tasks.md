# 102 — Registro de sensores · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Todas esperan a 001 T08 y T10, a
002 T05 y a 101 T03 (que crea `get_owned_or_404` y monta el patrón de rutas).

## A. Backend
- [ ] **T01 — Columna de clave y tabla de tipos** · FR-1.b, FR-1.c, FR-1.d, FR-1.e
  `app/models.py`: `Sensor.ingest_key_hash` (String(64), único, no nulo); `app/schemas.py`: `SENSOR_TYPES`.
  *Made when:* `.venv/bin/python -c "from app.schemas import SENSOR_TYPES; print(sorted(SENSOR_TYPES))"` imprime `['humidity', 'temperature']` y `grep -n "ingest_key_hash" app/models.py` lo encuentra.
- [ ] **T02 — Esquemas de sensor** · FR-1.f, FR-1.g, FR-1.h, FR-1.i, FR-1.j, FR-3.c, FR-3.d, FR-3.e · after T01
  `app/schemas.py`: `SensorCreate`, `SensorUpdate` (`extra="forbid"`), `SensorOut`, `SensorCreated`, `IngestKeyOut`.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and (fr1f or fr1g or fr1h or fr1j)" -q` pasa (los rechazos de esquema).
- [ ] **T03 — Registrar un sensor** · FR-1.a, FR-1.b, FR-1.c, FR-1.d, FR-1.e, FR-1.i · after T02
  `app/routers/sensors.py`: `_new_key()`, `hash_key()` y `POST /sensors`; `app/main.py`: montar el router.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr1" -q` pasa.
- [ ] **T04 — Ver mis sensores** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e · after T03
  `app/routers/sensors.py`: `GET /sensors` y `GET /sensors/{id}` con `get_owned_or_404`.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr2" -q` pasa.
- [ ] **T05 — Cambiar un sensor** · FR-3.a, FR-3.b, FR-3.c, FR-3.d, FR-3.e, FR-3.f · after T04
  `app/routers/sensors.py`: `PATCH /sensors/{id}` parcial (plan D4).
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr3" -q` pasa.
- [ ] **T06 — Regenerar la clave** · FR-4.a, FR-4.b, FR-4.c · after T04
  `app/routers/sensors.py`: `POST /sensors/{id}/ingest-key`.
  *Made when:* `.venv/bin/python -m pytest tests -k "102 and fr4" -q` pasa y la prueba de rutas sin token (NFR) devuelve 401 en las cinco rutas.

— checkpoint: sensores registrables, visibles, editables y con clave; `pytest -k 102` verde —

## B. Tests, migrations and tooling
- [ ] **T07 — Migración de la clave** · FR-1.c · after T01, 002 T07
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
