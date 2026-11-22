# 103 — Lecturas de sensores · Implementation plan

Status: draft · Spec: `spec.md` · Reference: `specs/sdd.profile.md`

## 1. Module structure

### A. Backend (`app/`)
| File | Holds | FR |
|---|---|---|
| `app/schemas.py` | `ReadingIn`, `ReadingOut`, `IngestOut`, `ConditionOut` | FR-1.b, FR-1.e, FR-2, FR-3 |
| `app/routers/readings.py` | tres rutas: recibir, historial, condiciones actuales; verificación de la clave | FR-1, FR-2, FR-3 |
| `app/deps.py` | usa `get_owned_or_404` (101 D1) | FR-2.f |
| `app/routers/sensors.py` | `hash_key()` (102) lo reutiliza la verificación | FR-1.c |
| `app/main.py` | monta el router | todos |
| `app/models.py` | `SensorReading` ya existe; sin cambios de columnas | — |

### B. Tests, migrations and tooling
| File | Holds | FR |
|---|---|---|
| `migrations/versions/…_readings_index.py` | índice `(sensor_id, recorded_at)` en `sensor_readings`; reemplaza `idx_sensor_readings_sensor_id`, que el compuesto ya cubre (002 D5) | FR-2.a, FR-2.b |
| `tests/test_103_sensor_readings.py` | plan §5 | todos |

## 2. Data model

Tabla `sensor_readings` (sin cambios de columnas; índice nuevo en negrita):

| Campo | Tipo | Null | Restricción |
|---|---|---|---|
| `id` | BigInteger | no | PK |
| `sensor_id` | BigInteger | no | FK → `sensors.id` |
| `value` | Numeric(5,2) | no | −999.99 a 999.99 |
| `recorded_at` | DateTime con zona | no | `now()` del servidor |
| **índice** | | | **`(sensor_id, recorded_at)`** |

Recibir (`POST /sensors/3/readings`, cabecera `X-Sensor-Key: <clave>`):

```json
{ "value": 78.5 }
```

Respuesta (`IngestOut`, 201):

```json
{ "id": 981, "sensor_id": 3, "value": 78.5, "recorded_at": "2026-11-13T13:00:02.114Z",
  "reading_interval_minutes": 60 }
```

Historial (`GET /sensors/3/readings?start=2026-11-13T00:00:00-03:00&end=2026-11-13T23:59:59-03:00&limit=2`):

```json
[ { "id": 981, "sensor_id": 3, "value": 78.5, "recorded_at": "2026-11-13T13:00:02.114Z" },
  { "id": 962, "sensor_id": 3, "value": 80.0, "recorded_at": "2026-11-13T12:00:01.870Z" } ]
```

Condiciones actuales (`GET /conditions`):

```json
[ { "sensor_id": 3, "name": "Humedad invernadero 1", "type": "humidity", "unit": "%",
    "min_val": 70.0, "max_val": 90.0, "value": 78.5, "recorded_at": "2026-11-13T13:00:02.114Z" },
  { "sensor_id": 4, "name": "Temperatura 1", "type": "temperature", "unit": "°C",
    "min_val": 18.0, "max_val": 24.0, "value": null, "recorded_at": null } ]
```

## 3. Surface

| Método y ruta | Autenticación | Filtro por dueño | Respuestas | FR |
|---|---|---|---|---|
| `POST /sensors/{sensor_id}/readings` | cabecera `X-Sensor-Key` (no bearer; enmienda de la regla 2, 102 D4) | la clave identifica al sensor | 201 `IngestOut`; 401 "Clave de sensor inválida"; 403 "Sensor inactivo"; 422 valor inválido | FR-1 |
| `GET /sensors/{sensor_id}/readings?start&end&limit` | bearer | `get_owned_or_404` sobre `Sensor` | 200 lista `ReadingOut`; 404 "Sensor no encontrado"; 422 `limit` > 1000, fechas sin zona o `start` > `end` | FR-2 |
| `GET /conditions` | bearer | sensores con `created_by` = cuenta y `is_active` | 200 lista `ConditionOut` por id de sensor | FR-3 |

`limit` por defecto 100, mínimo 1, máximo 1000. `start` y `end` exigen zona horaria (offset).

## 4. Technical decisions

**D1 — La clave se verifica con `hmac.compare_digest(hash_key(clave), sensor.ingest_key_hash)`; sensor inexistente y clave errónea responden lo mismo (401, mismo mensaje); cabecera ausente también (se declara opcional para no devolver 422).** Un sensor inexistente no hace la comparación, así que el tiempo de respuesta lo delata: `# ponytail: diferencia de tiempo aceptada, con 256 bits no hay adivinanza útil; añadir una comparación ficticia si importa`. *Discarded:* usar el bearer de la persona (ver 102 D4). (FR-1.c)

**D2 — `recorded_at` lo pone la base (`server_default now()`).** Tras el commit se hace `refresh` para devolverlo. *Discarded:* la hora que mande el dispositivo (spec D1). (FR-1.a)

**D3 — Orden de comprobaciones al recibir: clave (401) → sensor activo (403) → valor (422).** Así "Sensor inactivo" solo se le dice a quien tiene la clave. El valor se valida con `Decimal` (`max_digits=5`, `decimal_places=2`) en el esquema, por eso su 422 sale antes en la práctica; la prueba de FR-1.e lo comprueba con clave y sensor válidos. (FR-1.c–e)

**D4 — Historial: `WHERE sensor_id = :id AND recorded_at BETWEEN :start AND :end ORDER BY recorded_at DESC, id DESC LIMIT :limit`, apoyado en el índice `(sensor_id, recorded_at)`.** `start` y `end` son `AwareDatetime` (el nombre `from` es palabra reservada en Python). *Discarded:* `OFFSET` (spec D5). (FR-2)

**D5 — Condiciones actuales: una consulta por sensor activo para su última lectura (`ORDER BY recorded_at DESC, id DESC LIMIT 1`).** `# ponytail: una consulta por sensor; una persona tiene pocos sensores. Pasar a DISTINCT ON si crecen`. (FR-3)

**D6 — No existe ninguna ruta `PUT`, `PATCH` ni `DELETE` sobre lecturas, y ningún código las actualiza; `ReadingOut` no es editable.** FR-1.f se comprueba mirando `openapi.json` y el efecto de cambiar el sensor. (FR-1.f)

**D7 — 104 engancha su aviso aquí:** tras el commit de la lectura se llamará a la función de alertas de 104; este plan no la define, solo deja el punto en la ruta de recepción. (FR-1.a)

## 5. Test strategy

`tests/test_103_sensor_readings.py`, con la base de 002; cuentas A y B, un sensor de A (clave guardada de la
respuesta de creación) y otro de B. Una prueba pide historial y condiciones sin token y espera 401 (NFR).
Una prueba usa el token de A en lugar de la clave y espera 401 "Clave de sensor inválida".

| Bullet | Caso (Given / When / Then) | Kind |
|---|---|---|
| FR-1.a | Given un sensor activo de A con su clave / When el dispositivo envía 78.5 / Then hay una lectura de 78.5 con `recorded_at` entre antes y después de la petición | event |
| FR-1.b | Given esa lectura / When se lee la respuesta / Then trae id, `sensor_id`, valor, momento e intervalo del sensor | event |
| FR-1.c | Given clave ausente, clave de otro sensor, clave reemplazada (102 FR-4) y un sensor inexistente / When se envía / Then 401 "Clave de sensor inválida" en cada uno y la tabla sigue sin cambios | negative |
| FR-1.d | Given un sensor desactivado con su clave / When se envía / Then 403 "Sensor inactivo" y sin lectura | negative |
| FR-1.e | Given clave y sensor válidos / When se envían 1000, 1.234 y "caliente" / Then 422 en cada uno y sin lectura | negative |
| FR-1.f | Given lecturas guardadas / When se cambia el intervalo, se desactiva el sensor y se regenera la clave / Then las lecturas son idénticas, y `openapi.json` no declara `PUT`, `PATCH` ni `DELETE` bajo `/sensors/{id}/readings` | positive |
| FR-2.a | Given tres lecturas en distinto momento / When A pide el historial / Then salen de la más reciente a la más antigua | event |
| FR-2.b | Given lecturas en tres días / When A pide solo `start`, solo `end` y ambos / Then salen las del rango, extremos incluidos; sin ninguno, todas | both sides |
| FR-2.c | Given 150 lecturas / When A pide sin `limit` y con `limit=5` / Then 100 y 5 | positive |
| FR-2.d | Given cualquier historial / When A pide `limit=1001` / Then 422 | negative |
| FR-2.e | Given `start` posterior a `end` / When A pide / Then 422 | negative |
| FR-2.f | Given un sensor de B y un id inexistente / When A pide el historial / Then 404 "Sensor no encontrado" en ambos | negative |
| FR-3.a | Given dos sensores activos de A con lecturas / When A pide `/conditions` / Then cada uno trae sus datos, límites y la última lectura | event |
| FR-3.b | Given un sensor activo de A sin lecturas / When A pide `/conditions` / Then aparece con `value` y `recorded_at` nulos | state |
| FR-3.c | Given un sensor inactivo de A y uno de B / When A pide `/conditions` / Then ninguno aparece | positive |

## 6. Build order

1. Esquemas (`ReadingIn`, `ReadingOut`, `IngestOut`, `ConditionOut`).
2. `POST /sensors/{id}/readings` con verificación de clave (prueba primero) + montar el router.
3. `GET /sensors/{id}/readings`.
4. `GET /conditions`.
5. Índice (migración, tras 002 T07).

## 7. Requirement coverage

| FR | Plan sections |
|---|---|
| FR-1 | §1, §2, §3, §4 D1 D2 D3 D6 D7, §5 |
| FR-2 | §1, §2, §3, §4 D4, §5 |
| FR-3 | §1, §2, §3, §4 D5, §5 |
