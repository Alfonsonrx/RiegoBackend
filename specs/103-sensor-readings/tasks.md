# 103 — Lecturas de sensores · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Todas esperan a 102 T03 y T06 (sensores
con clave y su regeneración), a 001 T08 y T10 y a 002 T05.

## A. Backend
- [x] **T01 — Esquemas de lectura** · FR-1.b, FR-1.e, FR-2.a, FR-3.a
  `app/schemas.py`: `ReadingIn` (`Decimal`, 5 dígitos, 2 decimales), `ReadingOut`, `IngestOut`, `ConditionOut`.
  *Made when:* `.venv/bin/python -c "from app.schemas import IngestOut; print(list(IngestOut.model_fields))"` imprime `['id', 'sensor_id', 'value', 'recorded_at', 'reading_interval_minutes']`.
- [x] **T02 — Recibir una lectura** · FR-1.a, FR-1.b, FR-1.c, FR-1.d, FR-1.e · after T01
  `app/routers/readings.py`: `POST /sensors/{sensor_id}/readings` con `X-Sensor-Key` (plan D1–D3); `app/main.py`: montar el router.
  *Made when:* `.venv/bin/python -m pytest tests -k "103 and fr1" -q` pasa, salvo `fr1f`.
- [x] **T03 — Historial** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e, FR-2.f, FR-1.f · after T02
  `app/routers/readings.py`: `GET /sensors/{sensor_id}/readings` con `start`, `end`, `limit`; la prueba `fr1f` comprueba que no hay rutas de modificación ni borrado.
  *Made when:* `.venv/bin/python -m pytest tests -k "103 and (fr1f or fr2)" -q` pasa.
- [x] **T04 — Condiciones actuales** · FR-3.a, FR-3.b, FR-3.c · after T02
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
- 2026-11-17 · round 1 · base `d9776d8` (árbol limpio) · modo round.
- 2026-11-17 · T01 · done · `ReadingIn` (reusa `Limit`: Numeric(5,2)), `ReadingOut`, `IngestOut(ReadingOut)`, `ConditionOut`; sin prueba propia, las cubren T02–T04; finish line ok.
- 2026-11-17 · T02 · done · 5 pruebas fr1a–e (fallaron con 404: sin ruta) · `app/routers/readings.py` (clave con `hmac.compare_digest`, 401 → 403 → guardar) + montado en `main.py`; fr1c incluye id enorme y token de la persona en lugar de la clave; finish line ok.
- 2026-11-17 · T03 · done · 8 pruebas: fr1f, fr2a–f y fr2b_moment_without_zone (fallaron con 405: sin GET; fr1f solo en la comprobación de rutas) · `GET /sensors/{id}/readings` con `AwareDatetime`, `Query(ge=1, le=1000)` y `owned_sensor` de 102; mutación `>=`→`>` en `start` rompe fr2b; finish line ok.
- 2026-11-17 · T04 · done · 4 pruebas fr3a–c y security (fallaron con 404: sin `/conditions`) · `GET /conditions`, una consulta por sensor (plan D5), orden `NEWEST_FIRST` compartido con el historial; finish line ok.
- 2026-11-17 · round 1 · T01–T04 · gates green (import + 83 passed) · `sdd_check` 0 hallazgos, todos los bullets citados · floor: ninguna prueba borrada ni debilitada, sin `skip` ni supresiones (`app/routers/readings.py` era un archivo vacío desde el primer commit) · revisión: `true`, `"NaN"`, `"Infinity"` → 422; un número en texto (`"78.5"`) se acepta, igual que los límites de 102; sin propuestas para §10, sin hallazgos. T05 (índice) queda para el round 2.
