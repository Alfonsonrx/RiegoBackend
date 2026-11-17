# 101 — Calendario de riego · Implementation plan

Status: draft · Spec: `spec.md` · Reference: `specs/sdd.profile.md`

## 1. Module structure

### A. Backend (`app/`)
| File | Holds | FR |
|---|---|---|
| `app/config.py` | ajuste nuevo `TIMEZONE` (zona del invernadero); el módulo lo crea 001 T08 | FR-1.d, FR-3.b |
| `app/schemas.py` | `ScheduleCreate`, `ScheduleUpdate`, `ScheduleOut` | FR-1.b, FR-1.c, FR-3.a |
| `app/deps.py` | `get_owned_or_404(db, model, owner_column, id, user, detail)`: filtro por dueño y 404 en un solo sitio (lo reutilizan 102 y 104) | FR-2.b, FR-3.c |
| `app/routers/schedules.py` | router `/schedules`: crear, listar, cambiar; `local_now()` | FR-1, FR-2, FR-3 |
| `app/main.py` | monta el router | FR-1, FR-2, FR-3 |
| `app/models.py` | `IrrigationSchedule` ya existe; sin cambios aquí (104 añade `reminded_at`) | — |

### B. Tests, migrations and tooling
`tests/test_101_irrigation_schedule.py` (plan §5). Sin migración: el esquema no cambia.

## 2. Data model

Tabla `irrigation_schedule` (sin cambios):

| Campo | Tipo | Null | Restricción |
|---|---|---|---|
| `id` | BigInteger | no | PK |
| `created_by` | BigInteger | no | FK → `users.id`; es el dueño |
| `irrigation_date` | Date | no | |
| `irrigation_time` | Time | no | hora de pared de la zona `TIMEZONE` |
| `is_active` | Boolean | no | por defecto verdadero |

Representación de la API (`ScheduleOut`; no expone `created_by`):

```json
{ "id": 12, "irrigation_date": "2026-11-20", "irrigation_time": "08:00:00", "is_active": true }
```

Entrada: `ScheduleCreate` = `{ "irrigation_date": "2026-11-20", "irrigation_time": "08:00" }`;
`ScheduleUpdate` = cualquier subconjunto de `irrigation_date`, `irrigation_time`, `is_active` (ninguno
puede ser `null`).

## 3. Surface

| Método y ruta | Autenticación | Filtro por dueño | Respuestas | FR |
|---|---|---|---|---|
| `POST /schedules` | bearer | `created_by` = cuenta actual | 201 `ScheduleOut`; 400 "La fecha y hora de riego deben ser futuras"; 422 datos inválidos | FR-1 |
| `GET /schedules?active_only=true` | bearer | `created_by` = cuenta actual | 200 lista ordenada por fecha, hora, id | FR-2 |
| `PATCH /schedules/{id}` | bearer | `id` y `created_by` = cuenta actual | 200 `ScheduleOut`; 400 igual que arriba; 404 "Entrada de riego no encontrada" | FR-3 |

`active_only` por defecto es `false`.

## 4. Technical decisions

**D1 — Un único auxiliar `get_owned_or_404(db, model, owner_column, id, user, detail)` en `deps.py` aplica el filtro por dueño y lanza el 404 con el mensaje dado.** Lo usan 101, 102 y 104, así ninguna ruta puede olvidar el filtro. El listado filtra con la misma columna (`WHERE created_by = cuenta`). *Discarded:* un auxiliar por router (tres copias de lo mismo) y filtrar a mano en cada ruta (regla 1: un olvido filtra datos). (FR-3.c, FR-2.b)

**D2 — "Ahora" es `datetime.now(ZoneInfo(settings.TIMEZONE))` sin zona, comparado con `datetime.combine(fecha, hora)`; se encapsula en `local_now()` para fijarlo en pruebas.** El valor por defecto de `TIMEZONE` es `America/Santiago` (el brief es de una institución chilena; cámbiese por entorno). `zoneinfo` es de la biblioteca estándar. *Discarded:* hora del servidor (si corre en UTC corre las horas); librería de zonas (no hace falta). (FR-1.d, FR-3.b)

**D3 — `PATCH` parcial con `model_fields_set`; solo se revalida el futuro si el cambio modifica la fecha o la hora (traerlas con el mismo valor no cuenta, T06), usando la fecha u hora ya guardada para completar el par.** *Discarded:* `PUT` con reemplazo completo (obliga a reenviar todo para solo desactivar). (FR-3.a, FR-3.b)

**D4 — Orden por `irrigation_date`, `irrigation_time`, `id`** (el `id` desempata de forma estable). (FR-2.a)

**D5 — `active_only` es un parámetro de consulta, no una ruta aparte.** (FR-2.c)

## 5. Test strategy

`tests/test_101_irrigation_schedule.py`, con `TestClient` y la base de 002; dos cuentas (A y B) creadas por
la ruta de registro y sus tokens por la de inicio de sesión. `local_now()` se fija con `monkeypatch` a
2026-11-13 10:00. Una prueba más recorre las tres rutas sin token y espera 401 (NFR Security).

| Bullet | Caso (Given / When / Then) | Kind |
|---|---|---|
| FR-1.a | Given A autenticada / When envía 2026-11-20 y 08:00 / Then hay una entrada activa con `created_by` = A | event |
| FR-1.b | Given la creación anterior / When se lee la respuesta / Then trae id, fecha, hora y `is_active` verdadero | event |
| FR-1.c | Given A autenticada / When envía sin hora, y con la fecha "ayer-no" / Then 422 y la tabla sigue vacía | negative |
| FR-1.d | Given "ahora" fijo / When envía 2026-11-13 y 10:00 (igual) y 2026-11-13 y 09:00 / Then 400 con el mensaje y sin filas | negative |
| FR-2.a | Given tres entradas creadas en desorden / When A pide su calendario / Then vienen por fecha y hora ascendentes | event |
| FR-2.b | Given entradas de A y de B / When A pide su calendario / Then no aparece ninguna de B | positive |
| FR-2.c | Given una entrada activa y una inactiva / When A pide con y sin `active_only=true` / Then con el filtro solo la activa; sin él, ambas | both sides |
| FR-3.a | Given una entrada de A / When A cambia hora y luego `is_active` / Then cada cambio queda guardado y responde la entrada actualizada | event |
| FR-3.b | Given una entrada futura de A / When A le pone 2026-11-12 / Then 400 con el mensaje y la entrada intacta; y desactivar una entrada vencida sí funciona | negative |
| FR-3.b | Given una entrada vencida de A / When A la reenvía completa con su misma fecha y hora e `is_active` falso / Then 200 y queda inactiva | positive |
| FR-3.c | Given una entrada de B y un id inexistente / When A los cambia / Then 404 "Entrada de riego no encontrada" en ambos y la de B intacta | negative |
| FR-3.d | Given una entrada de A / When A envía `null` en fecha, hora o estado, o una hora inválida / Then 422 y la entrada intacta | negative |

## 6. Build order

1. `TIMEZONE` en `config.py` (tras 001 T08).
2. Esquemas.
3. `get_owned_or_404` en `deps.py`, `local_now()` y `POST /schedules` (prueba primero) + montar el router.
4. `GET /schedules`.
5. `PATCH /schedules/{id}`.

## 7. Requirement coverage

| FR | Plan sections |
|---|---|
| FR-1 | §1, §2, §3, §4 D2, §5 |
| FR-2 | §1, §3, §4 D1 D4 D5, §5 |
| FR-3 | §1, §2, §3, §4 D1 D2 D3, §5 |
