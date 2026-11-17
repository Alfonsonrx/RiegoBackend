# 104 — Notificaciones · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Esperan a 101 T05 (el `PATCH` del
calendario), 103 T02 (la recepción de lecturas), 001 T08 y T10 y 002 T05.

## A. Backend
- [ ] **T01 — Columna de recordatorio y esquema** · FR-1.a, FR-1.b, FR-3.a
  `app/models.py`: `IrrigationSchedule.reminded_at` (DateTime con zona, nulo); `app/schemas.py`: `NotificationOut`.
  *Made when:* `grep -n "reminded_at" app/models.py` lo encuentra y `.venv/bin/python -c "from app.schemas import NotificationOut; print(list(NotificationOut.model_fields))"` imprime `['id', 'type', 'is_read', 'message', 'created_at']`.
- [ ] **T02 — Recordatorios de riego** · FR-1.a, FR-1.b, FR-1.d, FR-1.e · after T01
  `app/notifications.py` (nuevo): `send_due_reminders(db, now)` con la sentencia atómica del plan D2 y el mensaje de recordatorio.
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and (fr1a or fr1b or fr1d or fr1e)" -q` pasa.
- [ ] **T03 — Reprogramar permite un recordatorio nuevo** · FR-1.c · after T02
  `app/routers/schedules.py`: el `PATCH` pone `reminded_at = NULL` si el cambio trae fecha u hora (plan D4).
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr1c" -q` pasa.
- [ ] **T04 — Bucle de revisión** · FR-1.a · after T02
  `app/notifications.py`: bucle cada 60 s con `asyncio.to_thread`; `app/main.py`: `lifespan` que lo arranca y lo cancela.
  *Made when:* las pruebas de intervalo de 60 s y de arranque/cancelación del `lifespan` pasan, y `uvicorn app.main:app` arranca y se apaga con Ctrl+C sin traza de error.
- [ ] **T05 — Alerta por lectura fuera de rango** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e · after T01
  `app/notifications.py`: `alert_if_out_of_range` y su mensaje; `app/routers/readings.py`: llamada tras el commit dentro de `try/except` (plan D5).
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr2" -q` pasa.
- [ ] **T06 — Ver mis notificaciones** · FR-3.a, FR-3.b, FR-3.c · after T01
  `app/routers/notifications.py`: `GET /notifications` con `unread_only`; `app/main.py`: montar el router.
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr3" -q` pasa.
- [ ] **T07 — Marcar como leída** · FR-4.a, FR-4.b · after T06
  `app/routers/notifications.py`: `PATCH /notifications/{id}/read` con `get_owned_or_404`.
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr4" -q` pasa y la prueba de rutas sin token devuelve 401.

— checkpoint: avisos de riego y de rango se crean, se listan y se marcan; `pytest -k 104` verde —

## B. Tests, migrations and tooling
- [ ] **T08 — Migración del recordatorio** · FR-1.b · after T01, 002 T07
  `migrations/versions/…`: agrega `irrigation_schedule.reminded_at` (nulo).
  *Made when:* `alembic upgrade head` añade la columna y `alembic downgrade -1` la quita.

## C. What could change
Nada pendiente. Canales fuera de la aplicación, paginación y avisos extra: `specs/backlog.md`.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T01, T02, T03, T04, T08 |
| FR-2 | T05 |
| FR-3 | T01, T06 |
| FR-4 | T07 |

## E. The gates

CI: ninguna definida. Locales: `.venv/bin/python -c "import app.main"` y `.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-15 · — · spec, plan y tasks escritos (draft) · sin tareas hechas.
