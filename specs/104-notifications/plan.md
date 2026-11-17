# 104 — Notificaciones · Implementation plan

Status: draft · Spec: `spec.md` · Reference: `specs/sdd.profile.md`

## 1. Module structure

### A. Backend (`app/`)
| File | Holds | FR |
|---|---|---|
| `app/models.py` | `IrrigationSchedule` gana `reminded_at` | FR-1.a, FR-1.b, FR-1.c |
| `app/notifications.py` | **nuevo**: `send_due_reminders(db, now)`, `alert_if_out_of_range(db, sensor, reading)`, redacción de los dos mensajes, bucle de revisión | FR-1, FR-2 |
| `app/schemas.py` | `NotificationOut` | FR-3.a, FR-4.a |
| `app/routers/notifications.py` | `GET /notifications`, `PATCH /notifications/{id}/read` | FR-3, FR-4 |
| `app/routers/schedules.py` | el `PATCH` (101) reinicia `reminded_at` si cambia fecha u hora | FR-1.c |
| `app/routers/readings.py` | la recepción (103) llama a `alert_if_out_of_range` tras el commit | FR-2 |
| `app/main.py` | `lifespan` que arranca y cancela el bucle; monta el router | FR-1 |
| `app/deps.py` | usa `get_owned_or_404` (101 D1) | FR-4.b |

### B. Tests, migrations and tooling
| File | Holds | FR |
|---|---|---|
| `migrations/versions/…_schedule_reminded_at.py` | agrega `irrigation_schedule.reminded_at` (nulo) | FR-1.b |
| `tests/test_104_notifications.py` | plan §5 | todos |

## 2. Data model

Tabla `notifications` (sin cambios):

| Campo | Tipo | Null | Restricción |
|---|---|---|---|
| `id` | BigInteger | no | PK |
| `user_id` | BigInteger | no | FK → `users.id`; es el dueño |
| `type` | String(30) | no | `irrigation_reminder` o `reading_alert` |
| `message` | Text | no | |
| `is_read` | Boolean | no | por defecto falso |
| `created_at` | DateTime con zona | sí | `now()` del servidor |

Tabla `irrigation_schedule`, columna nueva:

| Campo | Tipo | Null | Restricción |
|---|---|---|---|
| **`reminded_at`** | DateTime con zona | sí | **instante en que se creó el recordatorio; nulo = pendiente** |

Mensajes (constantes en `notifications.py`):

| Tipo | Forma | Ejemplo |
|---|---|---|
| `irrigation_reminder` | `Es hora de regar las orquídeas ({DD-MM-AAAA} {HH:MM})` | `Es hora de regar las orquídeas (20-11-2026 08:00)` |
| `reading_alert` | `{nombre}: {valor} {unidad} fuera de rango ({mín {min} {unidad}}{, }{máx {max} {unidad}})` con solo los límites que existan | `Humedad invernadero 1: 65 % fuera de rango (mín 70 %, máx 90 %)` |

Representación de la API (`NotificationOut`; no expone `user_id`):

```json
{ "id": 41, "type": "reading_alert", "is_read": false,
  "message": "Humedad invernadero 1: 65 % fuera de rango (mín 70 %, máx 90 %)",
  "created_at": "2026-11-13T13:00:02.300Z" }
```

## 3. Surface

| Método y ruta | Autenticación | Filtro por dueño | Respuestas | FR |
|---|---|---|---|---|
| `GET /notifications?unread_only=true` | bearer | `user_id` = cuenta actual | 200 lista de `NotificationOut`, 100 como máximo | FR-3 |
| `PATCH /notifications/{id}/read` | bearer | `id` y `user_id` = cuenta actual | 200 `NotificationOut`; 404 "Notificación no encontrada" | FR-4 |
| (interno) bucle de recordatorios | sin ruta | — | crea notificaciones | FR-1 |
| (interno) alerta tras guardar una lectura | sin ruta | — | crea una notificación | FR-2 |

`unread_only` por defecto es `false`. Ninguna ruta crea notificaciones.

## 4. Technical decisions

**D1 — El bucle es una tarea de `asyncio` iniciada en el `lifespan` de FastAPI: cada 60 s ejecuta `send_due_reminders` en un hilo (`asyncio.to_thread`) y se cancela al apagar.** *Discarded:* APScheduler o Celery (una dependencia nueva para un bucle de quince líneas); generar los recordatorios al consultar la lista (no existirían hasta que alguien mire y `created_at` mentiría). (FR-1.a)

**D2 — La revisión es una sola sentencia atómica:** `UPDATE irrigation_schedule SET reminded_at = now() WHERE is_active AND reminded_at IS NULL AND (irrigation_date + irrigation_time) <= :ahora_local RETURNING id, created_by, irrigation_date, irrigation_time`; con las filas devueltas se insertan las notificaciones en la misma transacción. Dos instancias no pueden reclamar la misma fila. *Discarded:* seleccionar y luego actualizar (dos procesos reciben la misma fila); un candado en memoria (no cubre varias instancias). (FR-1.a, FR-1.b, FR-1.d)

**D3 — "Ahora local" sale de `local_now()` (101 D2, zona `TIMEZONE`)**, que `send_due_reminders` recibe como parámetro para poder fijarlo en pruebas. (FR-1.a)

**D4 — El `PATCH` de 101 pone `reminded_at = NULL` cuando el cambio trae fecha u hora.** Cambiar solo `is_active` no lo toca. *Discarded:* reiniciarlo al reactivar (avisaría dos veces la misma cita). (FR-1.c, FR-1.b)

**D5 — `alert_if_out_of_range` se llama en la ruta de recepción (103) después del commit de la lectura, dentro de `try/except` que registra el error y sigue.** La lectura anterior es la de mayor `id` con `id` < el de la nueva para ese sensor. "Fuera de rango" es `valor < min_val` o `valor > max_val`, omitiendo el lado vacío. La alerta se crea en su propia transacción. *Discarded:* una sola transacción para lectura y alerta (si la alerta falla se perdería la lectura). (FR-2)

**D6 — Orden de la lista: `created_at DESC, id DESC`, `LIMIT 100`; `unread_only` filtra `is_read = false`.** (FR-3)

**D7 — Marcar como leída es idempotente: asigna `is_read = true` y devuelve la fila, aunque ya lo estuviera.** (FR-4.a)

**D8 — Migración con `reminded_at` nulo.** Las entradas ya existentes quedarían pendientes y recordarían si su momento ya pasó. Hoy la tabla no tiene filas (101 aún no existe), así que es inocuo. *Discarded:* rellenar con `now()` (innecesario hoy). (FR-1.b)

## 5. Test strategy

`tests/test_104_notifications.py`, con la base de 002; cuentas A y B. Los recordatorios se prueban llamando a
`send_due_reminders(db, ahora)` con un `ahora` fijo (2026-11-20 08:00), sin esperar al bucle; las alertas,
enviando lecturas por la ruta de recepción (103). Dos pruebas extra cubren la NFR de puntualidad: el
intervalo del bucle es 60 s (constante) y el `lifespan` arranca y cancela la tarea sin error. Una prueba
llama a las rutas sin token y espera 401.

| Bullet | Caso (Given / When / Then) | Kind |
|---|---|---|
| FR-1.a | Given dos entradas activas de A para el 2026-11-20 a las 08:00 sin recordatorio / When la revisión corre a las 08:00 en una y un día después (recordatorio tardío) en la otra / Then cada una genera una notificación `irrigation_reminder` no leída de A | event |
| FR-1.b | Given la entrada ya recordada / When corre la revisión otra vez, y dos revisiones simultáneas sobre otra entrada / Then sigue habiendo una sola notificación por entrada | event |
| FR-1.c | Given una entrada ya recordada / When A cambia su hora y corre la revisión al nuevo momento / Then hay una segunda notificación; y si solo cambia `is_active`, no | event |
| FR-1.d | Given una entrada inactiva con su momento pasado / When corre la revisión / Then no hay notificación | negative |
| FR-1.e | Given una entrada del 2026-11-20 a las 08:00 / When se crea su recordatorio / Then el mensaje es "Es hora de regar las orquídeas (20-11-2026 08:00)" | positive |
| FR-2.a | Given un sensor 70–90 sin lecturas y otro con última lectura 80 / When llegan 65 a cada uno / Then una `reading_alert` no leída para el dueño de cada uno | event |
| FR-2.b | Given una lectura de 65 ya alertada / When llega otra de 60 / Then no hay alerta nueva; y si llega 80 y luego 65, sí | negative |
| FR-2.c | Given un sensor con `min_val` vacío y `max_val` 90 / When llegan −50 y 95 / Then −50 no alerta y 95 sí; un sensor sin límites no alerta nunca | state |
| FR-2.d | Given el sensor "Humedad invernadero 1" 70–90 / When llega 65 / Then el mensaje es "Humedad invernadero 1: 65 % fuera de rango (mín 70 %, máx 90 %)" | positive |
| FR-2.e | Given `alert_if_out_of_range` forzada a lanzar una excepción / When llega 65 / Then la respuesta es 201 y la lectura está guardada | negative |
| FR-3.a | Given 120 notificaciones de A / When A las pide / Then salen 100, de la más reciente a la más antigua, con id, tipo, mensaje, `is_read` y fecha | event |
| FR-3.b | Given una leída y una no leída / When A pide con y sin `unread_only=true` / Then con el filtro solo la no leída; sin él, ambas | both sides |
| FR-3.c | Given notificaciones de A y de B / When A las pide / Then no sale ninguna de B | positive |
| FR-4.a | Given una notificación de A / When A la marca leída (dos veces) / Then `is_read` verdadero y la misma respuesta ambas veces | event |
| FR-4.b | Given una notificación de B y un id inexistente / When A las marca / Then 404 "Notificación no encontrada" y la de B sin cambios | negative |

## 6. Build order

1. Columna `reminded_at` y esquema `NotificationOut`.
2. `send_due_reminders` y sus mensajes (prueba primero).
3. Reinicio de `reminded_at` en el `PATCH` de 101.
4. Bucle de fondo en el `lifespan`.
5. `alert_if_out_of_range` y su llamada desde la recepción de 103.
6. `GET /notifications` y `PATCH /notifications/{id}/read` + montar el router.
7. Migración (tras 002 T07).

## 7. Requirement coverage

| FR | Plan sections |
|---|---|
| FR-1 | §1, §2, §3, §4 D1 D2 D3 D4 D8, §5 |
| FR-2 | §1, §2, §3, §4 D5, §5 |
| FR-3 | §1, §2, §3, §4 D6, §5 |
| FR-4 | §1, §2, §3, §4 D7, §5 |
