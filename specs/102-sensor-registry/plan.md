# 102 — Registro de sensores · Implementation plan

Status: draft · Spec: `spec.md` · Reference: `specs/sdd.profile.md`

## 1. Module structure

### A. Backend (`app/`)
| File | Holds | FR |
|---|---|---|
| `app/models.py` | `Sensor` gana `ingest_key_hash` | FR-1.b, FR-1.c, FR-4.a |
| `app/schemas.py` | `SENSOR_TYPES`, `SensorCreate`, `SensorUpdate`, `SensorOut`, `SensorCreated`, `IngestKeyOut` | FR-1, FR-2, FR-3, FR-4 |
| `app/routers/sensors.py` | router `/sensors`: crear, listar, ver, cambiar, regenerar clave; `_new_key()`, `hash_key()` | FR-1 a FR-4 |
| `app/deps.py` | usa `get_owned_or_404` (plan 101 D1) | FR-2.e, FR-3.f, FR-4.c |
| `app/main.py` | monta el router | todos |

### B. Tests, migrations and tooling
| File | Holds | FR |
|---|---|---|
| `migrations/versions/…_sensor_ingest_key.py` | agrega `sensors.ingest_key_hash` (no nulo, único) | FR-1.c |
| `tests/test_102_sensor_registry.py` | plan §5 | todos |

## 2. Data model

Tabla `sensors` (cambio en negrita):

| Campo | Tipo | Null | Restricción |
|---|---|---|---|
| `id` | BigInteger | no | PK |
| `created_by` | BigInteger | no | FK → `users.id` |
| `name` | String(100) | no | |
| `type` | String(20) | no | `humidity` o `temperature` |
| `unit` | String(20) | no | derivada del tipo |
| `connection_type` | String(20) | no | `wifi` o `bluetooth` |
| `min_val`, `max_val` | Numeric(5,2) | sí | inferior ≤ superior si ambos existen |
| `reading_interval_minutes` | Integer | no | ≥ 1 |
| `is_active` | Boolean | no | por defecto verdadero |
| **`ingest_key_hash`** | String(64) | no | **único; SHA-256 hexadecimal de la clave** |

Valores por tipo (constante `SENSOR_TYPES` en `schemas.py`, única fuente):

| Tipo | Unidad | Límite inferior | Límite superior |
|---|---|---|---|
| `humidity` | `%` | 70 | 90 |
| `temperature` | `°C` | 18 | 24 |

Crear (`SensorCreate`):

```json
{ "name": "Humedad invernadero 1", "type": "humidity", "connection_type": "wifi",
  "reading_interval_minutes": 60 }
```

Respuesta al crear (`SensorCreated`; la clave solo aparece aquí y al regenerar):

```json
{ "id": 3, "name": "Humedad invernadero 1", "type": "humidity", "unit": "%",
  "connection_type": "wifi", "reading_interval_minutes": 60,
  "min_val": 70.0, "max_val": 90.0, "is_active": true,
  "ingest_key": "<43 caracteres url-safe, mostrados una vez>" }
```

`SensorOut` es lo mismo sin `ingest_key`. `IngestKeyOut` = `{ "ingest_key": "…" }`. `SensorUpdate` acepta solo
`name`, `reading_interval_minutes`, `min_val`, `max_val`, `is_active` (`extra="forbid"`; `min_val` y
`max_val` pueden ser `null`). Los límites salen como número (`float`), no como texto.

## 3. Surface

| Método y ruta | Autenticación | Filtro por dueño | Respuestas | FR |
|---|---|---|---|---|
| `POST /sensors` | bearer | `created_by` = cuenta actual | 201 `SensorCreated`; 422 datos inválidos | FR-1 |
| `GET /sensors` | bearer | `created_by` = cuenta actual | 200 lista de `SensorOut` por id | FR-2.a–c |
| `GET /sensors/{id}` | bearer | `id` y `created_by` | 200 `SensorOut`; 404 "Sensor no encontrado" | FR-2.d, FR-2.e |
| `PATCH /sensors/{id}` | bearer | `id` y `created_by` | 200 `SensorOut`; 404; 422 datos inválidos o campos no permitidos | FR-3 |
| `POST /sensors/{id}/ingest-key` | bearer | `id` y `created_by` | 200 `IngestKeyOut`; 404 | FR-4 |

## 4. Technical decisions

**D1 — Clave = `secrets.token_urlsafe(32)` (256 bits); se guarda `hashlib.sha256(clave).hexdigest()`.** *Discarded:* bcrypt (pensado para contraseñas de poca entropía; verificar una clave en cada lectura sería lento sin ganar seguridad con 256 bits aleatorios); guardar la clave en claro (la robaría quien lea la base). La comparación al recibir lecturas usa `hmac.compare_digest` (103). (FR-1.b, FR-1.c)

**D2 — Tipos y conexiones como `Literal` de Pydantic y la tabla `SENSOR_TYPES` en un solo sitio.** Ampliarlas es agregar una entrada. *Discarded:* tabla de tipos en la base (ningún requisito la necesita). (FR-1.d–g)

**D3 — Validación de intervalo y límites en el esquema (`Field(ge=1)`, `Decimal` con `max_digits=5` y `decimal_places=2`); el orden inferior ≤ superior lo valida `check_limits()` en la ruta, con los valores ya completados por los defaults (al crear) o mezclados con los guardados (al cambiar), con un solo mensaje: "El límite inferior no puede ser mayor que el superior" (round 1: antes decía "en el esquema").** *Discarded:* confiar en la base (devolvería un error de servidor, no un 422). (FR-1.h–j, FR-3.c, FR-3.d)

**D4 — `PATCH` parcial con `model_fields_set`; un `null` explícito solo se acepta en `min_val` y `max_val`.** `extra="forbid"` produce el rechazo de FR-3.e. *Discarded:* campos extra ignorados en silencio (la persona creería haber cambiado el tipo). (FR-3)

**D5 — Reutiliza `get_owned_or_404` (101 D1) para sensores.** (FR-2.e, FR-3.f, FR-4.c)

**D6 — Migración que agrega `ingest_key_hash` como `NOT NULL`.** Hoy ningún código escribe sensores, así que la tabla debe estar vacía; si una base de desarrollo tiene filas, hay que vaciarla antes. *Discarded:* columna nula (dejaría sensores que nunca podrían enviar lecturas). (FR-1.c)

## 5. Test strategy

`tests/test_102_sensor_registry.py`, con la base de 002, dos cuentas A y B y sus tokens. Una prueba
recorre las cinco rutas sin token y espera 401 (NFR Security). Una prueba lee la fila y comprueba que
`ingest_key_hash` ≠ la clave entregada y = su SHA-256.

| Bullet | Caso (Given / When / Then) | Kind |
|---|---|---|
| FR-1.a | Given A autenticada / When crea un sensor válido / Then hay un sensor activo con `created_by` = A | event |
| FR-1.b | Given esa creación / When se lee la respuesta / Then trae los datos y `ingest_key` | event |
| FR-1.c | Given el sensor creado / When se lee la fila / Then `ingest_key_hash` = SHA-256 de la clave y no la contiene | positive |
| FR-1.d | Given un sensor `humidity` y uno `temperature` / When se crean / Then sus unidades son `%` y `°C` | positive |
| FR-1.e | Given un `humidity` sin límites, uno con solo `min_val`=75 y un `temperature` sin límites / When se crean / Then 70–90, 75–90 y 18–24 | event |
| FR-1.f | Given el tipo "soil_moisture" / When se crea / Then 422 y sin sensor | negative |
| FR-1.g | Given la conexión "lora" / When se crea / Then 422 y sin sensor | negative |
| FR-1.h | Given intervalos 0, −5, 1.5 y "diez" / When se crea / Then 422 en cada uno | negative |
| FR-1.i | Given `humidity` con `min_val`=95 (superior por defecto 90) / When se crea / Then 422 | negative |
| FR-1.j | Given `max_val`=1000 y `min_val`=1.234 / When se crea / Then 422 en cada uno | negative |
| FR-2.a | Given dos sensores de A / When A los lista / Then salen ambos con todos sus campos | event |
| FR-2.b | Given sensores de A y de B / When A los lista / Then no sale ninguno de B | positive |
| FR-2.c | Given un sensor / When se consulta, se cambia y se lista / Then ninguna respuesta lleva `ingest_key` ni `ingest_key_hash` | positive |
| FR-2.d | Given un sensor de A / When A lo pide por id / Then recibe sus datos | event |
| FR-2.e | Given un sensor de B y un id inexistente / When A los pide / Then 404 "Sensor no encontrado" en ambos | negative |
| FR-3.a | Given un sensor de A / When A cambia nombre, intervalo, límites y `is_active` / Then se guarda y la respuesta lo refleja | event |
| FR-3.b | Given un sensor con límites / When A envía `min_val: null` / Then el límite queda vacío y el otro se conserva | event |
| FR-3.c | Given 70–90 / When A envía `min_val`=95 / Then 422 y el sensor intacto | negative |
| FR-3.d | Given un sensor / When A envía `reading_interval_minutes`=0 / Then 422 y el sensor intacto | negative |
| FR-3.e | Given un sensor / When A envía `type`, `unit` o `connection_type` / Then 422 y el sensor intacto | negative |
| FR-3.f | Given un sensor de B y un id inexistente / When A los cambia / Then 404 y el de B intacto | negative |
| FR-4.a | Given un sensor de A / When A pide clave nueva / Then `ingest_key_hash` cambia | event |
| FR-4.b | Given esa petición / When se lee la respuesta / Then trae la clave nueva y su SHA-256 es el guardado | event |
| FR-4.c | Given un sensor de B y un id inexistente / When A pide clave / Then 404 y el hash de B intacto | negative |

## 6. Build order

1. Modelo (`ingest_key_hash`) y constantes en `schemas.py`.
2. Esquemas.
3. `POST /sensors` con clave (prueba primero) y montar el router.
4. `GET /sensors` y `GET /sensors/{id}`.
5. `PATCH /sensors/{id}`.
6. `POST /sensors/{id}/ingest-key`.
7. Migración (tras 002 T07).

## 7. Requirement coverage

| FR | Plan sections |
|---|---|
| FR-1 | §1, §2, §3, §4 D1 D2 D3 D6, §5 |
| FR-2 | §1, §2, §3, §4 D5, §5 |
| FR-3 | §1, §2, §3, §4 D3 D4 D5, §5 |
| FR-4 | §1, §3, §4 D1 D5, §5 |
