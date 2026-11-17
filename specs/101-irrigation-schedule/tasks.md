# 101 — Calendario de riego · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Todas esperan a 001 T08 (módulo de
configuración), 001 T10 (router de auth montado, para obtener tokens) y 002 T05 (base de pruebas).

## A. Backend
- [ ] **T01 — Ajuste de zona horaria** · FR-1.d, FR-3.b · after 001 T08
  `app/config.py`: `TIMEZONE` (por defecto `America/Santiago`).
  *Made when:* `.venv/bin/python -c "from app.config import get_settings; print(get_settings().TIMEZONE)"` imprime la zona.
- [ ] **T02 — Esquemas de calendario** · FR-1.b, FR-1.c, FR-3.a · after T01
  `app/schemas.py`: `ScheduleCreate`, `ScheduleUpdate` (sin `null`), `ScheduleOut`.
  *Made when:* `.venv/bin/python -c "from app.schemas import ScheduleOut; print(list(ScheduleOut.model_fields))"` imprime `['id', 'irrigation_date', 'irrigation_time', 'is_active']`.
- [ ] **T03 — Crear entrada y montar el router** · FR-1.a, FR-1.b, FR-1.c, FR-1.d · after T02
  `app/deps.py`: `get_owned_or_404`; `app/routers/schedules.py`: `local_now()` y `POST /schedules`; `app/main.py`: `include_router`.
  *Made when:* `.venv/bin/python -m pytest tests -k "101 and fr1" -q` pasa.
- [ ] **T04 — Ver el calendario** · FR-2.a, FR-2.b, FR-2.c · after T03
  `app/routers/schedules.py`: `GET /schedules` con `active_only`.
  *Made when:* `.venv/bin/python -m pytest tests -k "101 and fr2" -q` pasa.
- [ ] **T05 — Cambiar una entrada** · FR-3.a, FR-3.b, FR-3.c · after T03
  `app/routers/schedules.py`: `PATCH /schedules/{id}` con revalidación parcial (plan D3).
  *Made when:* `.venv/bin/python -m pytest tests -k "101 and fr3" -q` pasa y la prueba de rutas sin token (NFR) devuelve 401 en las tres rutas.

— checkpoint: el calendario se crea, se ve y se cambia por la API; `pytest -k 101` verde —

## B. Tests, migrations and tooling
Sin cambios de esquema ni de dependencias: no hay migración. Las pruebas viven con cada tarea de §A.

## C. What could change
Nada pendiente. Entradas recurrentes y borrado: `specs/backlog.md`.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T01, T02, T03 |
| FR-2 | T04 |
| FR-3 | T01, T02, T05 |

## E. The gates

CI: ninguna definida. Locales: `.venv/bin/python -c "import app.main"` y `.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-13 · — · spec, plan y tasks escritos (draft) · sin tareas hechas.
