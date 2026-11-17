# 104 — Notificaciones · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Esperan a 101 T05 (el `PATCH` del
calendario), 103 T02 (la recepción de lecturas), 001 T08 y T10 y 002 T05.

## A. Backend
- [x] **T01 — Columna de recordatorio y esquema** · FR-1.a, FR-1.b, FR-3.a
  `app/models.py`: `IrrigationSchedule.reminded_at` (DateTime con zona, nulo); `app/schemas.py`: `NotificationOut`.
  *Made when:* `grep -n "reminded_at" app/models.py` lo encuentra y `.venv/bin/python -c "from app.schemas import NotificationOut; print(list(NotificationOut.model_fields))"` imprime `['id', 'type', 'is_read', 'message', 'created_at']`.
- [x] **T02 — Recordatorios de riego** · FR-1.a, FR-1.b, FR-1.d, FR-1.e · after T01
  `app/notifications.py` (nuevo): `send_due_reminders(db, now)` con la sentencia atómica del plan D2 y el mensaje de recordatorio.
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and (fr1a or fr1b or fr1d or fr1e)" -q` pasa.
- [x] **T03 — Reprogramar permite un recordatorio nuevo** · FR-1.c · after T02
  `app/routers/schedules.py`: el `PATCH` pone `reminded_at = NULL` si el cambio trae fecha u hora (plan D4).
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr1c" -q` pasa.
- [x] **T04 — Bucle de revisión** · FR-1.a · after T02
  `app/notifications.py`: bucle cada 60 s con `asyncio.to_thread`; `app/main.py`: `lifespan` que lo arranca y lo cancela.
  *Made when:* las pruebas de intervalo de 60 s y de arranque/cancelación del `lifespan` pasan, y `uvicorn app.main:app` arranca y se apaga con Ctrl+C sin traza de error.
- [x] **T05 — Alerta por lectura fuera de rango** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e · after T01
  `app/notifications.py`: `alert_if_out_of_range` y su mensaje; `app/routers/readings.py`: llamada tras el commit dentro de `try/except` (plan D5).
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr2" -q` pasa.
- [x] **T06 — Ver mis notificaciones** · FR-3.a, FR-3.b, FR-3.c · after T01
  `app/routers/notifications.py`: `GET /notifications` con `unread_only`; `app/main.py`: montar el router.
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr3" -q` pasa.
- [x] **T07 — Marcar como leída** · FR-4.a, FR-4.b · after T06
  `app/routers/notifications.py`: `PATCH /notifications/{id}/read` con `get_owned_or_404`.
  *Made when:* `.venv/bin/python -m pytest tests -k "104 and fr4" -q` pasa y la prueba de rutas sin token devuelve 401.

— checkpoint: avisos de riego y de rango se crean, se listan y se marcan; `pytest -k 104` verde —

## B. Tests, migrations and tooling
- [x] **T08 — Migración del recordatorio** · FR-1.b · after T01, 002 T07
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
- 2026-11-17 · round 1 · base `339e790` (árbol limpio) · modo round.
- 2026-11-17 · T01 · done · `IrrigationSchedule.reminded_at` (DateTime con zona, nulo) y `NotificationOut`; finish line ok.
- 2026-11-17 · T08 · done (adelantada, como 102 T07: las pruebas construyen la base desde las migraciones y 002 fr1b compara modelos con migraciones) · `fdfdba988c82_schedule_reminded_at.py`; 002 fr1b falló con `add_column reminded_at` antes y pasa después; upgrade/downgrade -1/upgrade en la base de prueba ok.
- 2026-11-17 · T02 · done · 4 pruebas fr1a, fr1b (incluye dos revisiones simultáneas en hilos), fr1d, fr1e (fallaron: sin `app/notifications.py`) · `send_due_reminders` con el `UPDATE … RETURNING` del plan D2; mutaciones: sin `reminded_at IS NULL` rompe fr1b, sin `is_active` rompe fr1d; finish line ok.
- 2026-11-17 · T03 · done · 1 prueba fr1c por la API (falló: sin segundo recordatorio tras mover la hora) · el `PATCH` de 101 pone `reminded_at = None` solo cuando cambia fecha u hora; reactivar o reenviar el mismo momento no; 101 sigue verde (14); finish line ok.
- 2026-11-17 · T04 · done · 2 pruebas de puntualidad (fallaron: sin `REVIEW_EVERY_S` ni bucle): intervalo 60 s, y el `lifespan` arranca la revisión, sobrevive a un error y se cancela al salir · `review_loop` con `asyncio.to_thread` + `try/except` que registra y sigue; `lifespan` en `main.py`; `uvicorn` contra la base de prueba arranca y se apaga con SIGINT, código 0, sin traza; finish line ok.
- 2026-11-17 · T05 · done · 5 pruebas fr2a–e por la ruta de recepción de 103 (fallaron: ninguna alerta, sin `alert_if_out_of_range`) · `alert_if_out_of_range` (límites inclusivos, lado vacío sin tope, lectura anterior = mayor id menor) y su llamada en `readings.py` tras el commit, dentro de `try/except` que registra; la respuesta se arma antes de la alerta. Una corrección de la preparación en fr2d: crear con `min_val: null` toma el default (102 FR-1.e), así que el límite se vacía con un `PATCH`; la aserción no cambió. Mutaciones: sin la comprobación de la lectura anterior rompe fr2b; `<=` en el mínimo rompe fr2a; 103 sigue verde (17); finish line ok.
- 2026-11-17 · T06 · done · 3 pruebas fr3a–c (fallaron con 404: sin ruta) · `GET /notifications` con `unread_only`, `created_at DESC, id DESC`, tope 100; montado en `main.py` como `notifications_routes` (el módulo `app.notifications` ya usa el nombre); finish line ok.
- 2026-11-17 · T07 · done · 3 pruebas fr4a, fr4b y security (fallaron con 404) · `PATCH /notifications/{id}/read` con `get_owned_or_404`, idempotente; finish line ok.
- 2026-11-17 · round 1 · T01–T08 (T08 adelantada) · gates green (import + 101 passed) · `sdd_check` 0 hallazgos, todos los bullets citados · floor: ninguna línea de prueba borrada, sin `skip` ni supresiones · revisión: se añadió a la prueba de seguridad que ninguna ruta pública crea notificaciones (solo `get` y `patch` bajo `/notifications`, NFR Security); la base real tiene 0 entradas de calendario, así que el plan D8 (recordatorios tardíos al migrar) es inocuo; los valores de las alertas usan punto decimal ("25.5 °C"), el spec no fija separador; sin propuestas para §10, sin hallazgos.
