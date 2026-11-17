# 103 — Lecturas de sensores · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Todas esperan a 102 T03 y T06 (sensores
con clave y su regeneración), a 001 T08 y T10 y a 002 T05.

## A. Backend
- [ ] **T01 — Esquemas de lectura** · FR-1.b, FR-1.e, FR-2.a, FR-3.a
  `app/schemas.py`: `ReadingIn` (`Decimal`, 5 dígitos, 2 decimales), `ReadingOut`, `IngestOut`, `ConditionOut`.
  *Made when:* `.venv/bin/python -c "from app.schemas import IngestOut; print(list(IngestOut.model_fields))"` imprime `['id', 'sensor_id', 'value', 'recorded_at', 'reading_interval_minutes']`.
- [ ] **T02 — Recibir una lectura** · FR-1.a, FR-1.b, FR-1.c, FR-1.d, FR-1.e · after T01
  `app/routers/readings.py`: `POST /sensors/{sensor_id}/readings` con `X-Sensor-Key` (plan D1–D3); `app/main.py`: montar el router.
  *Made when:* `.venv/bin/python -m pytest tests -k "103 and fr1" -q` pasa, salvo `fr1f`.
- [ ] **T03 — Historial** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e, FR-2.f, FR-1.f · after T02
  `app/routers/readings.py`: `GET /sensors/{sensor_id}/readings` con `start`, `end`, `limit`; la prueba `fr1f` comprueba que no hay rutas de modificación ni borrado.
  *Made when:* `.venv/bin/python -m pytest tests -k "103 and (fr1f or fr2)" -q` pasa.
- [ ] **T04 — Condiciones actuales** · FR-3.a, FR-3.b, FR-3.c · after T02
  `app/routers/readings.py`: `GET /conditions` (plan D5).
  *Made when:* `.venv/bin/python -m pytest tests -k "103 and fr3" -q` pasa y la prueba de rutas sin token (NFR) devuelve 401 en historial y condiciones.

— checkpoint: un dispositivo guarda lecturas y la persona ve historial y valores actuales; `pytest -k 103` verde —

## B. Tests, migrations and tooling
- [ ] **T05 — Índice del historial** · FR-2.a, FR-2.b · after 002 T07
  `migrations/versions/…`: índice `(sensor_id, recorded_at)` en `sensor_readings` y borrar `idx_sensor_readings_sensor_id` (002 D5).
  *Made when:* `alembic upgrade head` crea el índice (`\d sensor_readings` en `psql` lo lista) y `alembic downgrade -1` lo quita.

## C. What could change
Nada pendiente. Protocolo del dispositivo, agregados y purga: `specs/backlog.md`.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T01, T02, T03 |
| FR-2 | T01, T03, T05 |
| FR-3 | T01, T04 |

## E. The gates

CI: ninguna definida. Locales: `.venv/bin/python -c "import app.main"` y `.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-15 · — · spec, plan y tasks escritos (draft) · sin tareas hechas.
