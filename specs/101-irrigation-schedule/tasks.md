# 101 — Calendario de riego · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. Todas esperan a 001 T08 (módulo de
configuración), 001 T10 (router de auth montado, para obtener tokens) y 002 T05 (base de pruebas).

## A. Backend
- [x] **T01 — Ajuste de zona horaria** · FR-1.d, FR-3.b · after 001 T08
  `app/config.py`: `TIMEZONE` (por defecto `America/Santiago`).
  *Made when:* `.venv/bin/python -c "from app.config import get_settings; print(get_settings().TIMEZONE)"` imprime la zona.
- [x] **T02 — Esquemas de calendario** · FR-1.b, FR-1.c, FR-3.a · after T01
  `app/schemas.py`: `ScheduleCreate`, `ScheduleUpdate` (sin `null`), `ScheduleOut`.
  *Made when:* `.venv/bin/python -c "from app.schemas import ScheduleOut; print(list(ScheduleOut.model_fields))"` imprime `['id', 'irrigation_date', 'irrigation_time', 'is_active']`.
- [x] **T03 — Crear entrada y montar el router** · FR-1.a, FR-1.b, FR-1.c, FR-1.d · after T02
  `app/deps.py`: `get_owned_or_404`; `app/routers/schedules.py`: `local_now()` y `POST /schedules`; `app/main.py`: `include_router`.
  *Made when:* `.venv/bin/python -m pytest tests -k "101 and fr1" -q` pasa.
- [x] **T04 — Ver el calendario** · FR-2.a, FR-2.b, FR-2.c · after T03
  `app/routers/schedules.py`: `GET /schedules` con `active_only`.
  *Made when:* `.venv/bin/python -m pytest tests -k "101 and fr2" -q` pasa.
- [x] **T05 — Cambiar una entrada** · FR-3.a, FR-3.b, FR-3.c, FR-3.d · after T03
  `app/routers/schedules.py`: `PATCH /schedules/{id}` con revalidación parcial (plan D3).
  *Made when:* `.venv/bin/python -m pytest tests -k "101 and fr3" -q` pasa y la prueba de rutas sin token (NFR) devuelve 401 en las tres rutas.

— checkpoint: el calendario se crea, se ve y se cambia por la API; `pytest -k 101` verde —

## B. Tests, migrations and tooling
Sin cambios de esquema ni de dependencias: no hay migración. Las pruebas viven con cada tarea de §A.

## C. What could change
- [x] **T06 — Reenviar fecha y hora sin cambiarlas no revalida** · FR-3.a, FR-3.b · after T05
  `app/routers/schedules.py`: revalidar solo si la fecha o la hora enviadas difieren de las guardadas (hoy basta con que vengan). Fallo hallado en la revisión de round 1: una interfaz que reenvía la entrada completa con `is_active: false` no puede desactivar una entrada vencida (400).
  *Made when:* `.venv/bin/python -m pytest tests -k "101 and fr3" -q` pasa con un caso nuevo: entrada vencida + `PATCH` con su misma fecha y hora y `is_active: false` → 200.
- ~~T07 — Zona horaria válida en toda plataforma~~ · descartada por la persona dueña (spec §10, 2026-11-17).

Entradas recurrentes y borrado: `specs/backlog.md`.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T01, T02, T03 |
| FR-2 | T04 |
| FR-3 | T01, T02, T05, T06 |

## E. The gates

CI: ninguna definida. Locales: `.venv/bin/python -c "import app.main"` y `.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-13 · — · spec, plan y tasks escritos (draft) · sin tareas hechas.
- 2026-11-17 · base · `d291262` · árbol limpio · round 1 (modo round) T01–T05.
- 2026-11-17 · T01 · done · `TIMEZONE` en `config.py`; *Made when* imprime `America/Santiago`. Sin prueba propia: la cubre `test_101_fr1d_now_is_greenhouse_wall_clock` (T03).
- 2026-11-17 · T02 · done · `ScheduleCreate`, `ScheduleUpdate` (omitible, nunca `null`: el default no se valida), `ScheduleOut`; tipo `WallTime` rechaza horas con zona (`08:00+02:00` haría fallar con 500 la comparación con la hora local). *Made when* ok.
- 2026-11-17 · T03 · done · `POST /schedules`, `local_now()`, `require_future()`, router montado; 5 pruebas FR-1 (incluida la zona: con `Pacific/Kiritimati` la hora del servidor o UTC fallarían). Rojo: `schedules` sin `local_now`. `get_owned_or_404` pasa a T05, donde se usa por primera vez.
- 2026-11-17 · T04 · done · `GET /schedules` con `active_only`, orden fecha, hora, id; 3 pruebas FR-2 (rojo: 405 sin la ruta). FR-2.c crea la entrada inactiva directo en la base para no depender de T05.
- 2026-11-17 · T05 · done · `PATCH /schedules/{id}` parcial (revalida solo si cambia fecha u hora, completando el par con lo guardado); `get_owned_or_404` en `deps.py`; 4 pruebas FR-3 (rojo: 405) + `test_101_fr3_null_or_invalid_change_rejected` (sin bullet: ver §10) + prueba sin token en las tres rutas (su primer rojo fue un error de la prueba, `get(json=)`, corregido con `request()`; la aserción no cambió).
- 2026-11-17 · round 1 · T01–T05 · gates green (import + 38 passed) · floor: sin pruebas borradas, saltadas ni debilitadas, sin supresiones · revisión: id enorme → 404, `PATCH {}` → 200 sin cambios; 1 fallo → T06; propuestas FR-3.d y `tzdata` (§10) → T07; aviso passlib/bcrypt → backlog.
- 2026-11-17 · base · round 2 sobre `d291262` + round 1 sin confirmar · T06 (T07 descartada por la persona dueña).
- 2026-11-17 · — · decisiones de la persona dueña: FR-3.d aceptado (D7; prueba renombrada a `test_101_fr3d_…`), `tzdata`/T07 rechazado; FR-3.b reescrito a "modifica la fecha o la hora" (D8) y 104 plan D4 alineado.
- 2026-11-17 · T06 · done · `test_101_fr3b_resending_same_date_time_is_not_a_change` (rojo: 400 al reenviar fecha y hora iguales de una entrada vencida); el `PATCH` revalida solo si el par fecha-hora difiere del guardado.
- 2026-11-17 · round 2 · T06 · gates green (import + 39 passed) · floor: 13 → 14 pruebas, una renombrada (`fr3` → `fr3d`), ninguna aserción quitada, sin supresiones · revisión: sin hallazgos nuevos.
