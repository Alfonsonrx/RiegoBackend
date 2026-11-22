# RiegoBackend
Backend en FastAPI para la gestión de riego de un invernadero de orquídeas.

## Instalación

Requisitos: Python 3 (probado con 3.14) y PostgreSQL.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # completar DB_*, TEST_DB_NAME y SECRET_KEY
```

Crear dos bases vacías en PostgreSQL, una para `DB_NAME` y otra para `TEST_DB_NAME`, cuyo dueño sea
`DB_USER`.

## Base de datos (Alembic)

La estructura de la base la crean **solo** las migraciones de `migrations/versions/`. La aplicación no
crea ni cambia tablas al arrancar.

```bash
.venv/bin/alembic upgrade head    # crea o actualiza la estructura; repetirlo tras cada `git pull`
```

Si `/db-check` responde `{"db":"ok"}` pero las rutas fallan con *relation ... does not exist*, falta
este paso: `/db-check` solo prueba que la base responde.

**Base creada antes de usar Alembic** (ya tiene las tablas, sin tabla `alembic_version`): marcarla una vez
con `alembic stamp head` y comprobar con `alembic check` que no hay diferencias. Si las hay, lo más simple
en desarrollo es borrar la base, crearla vacía y correr `alembic upgrade head`.

### Cambiar el esquema

1. Editar los modelos en `app/models.py`.
2. `.venv/bin/alembic upgrade head` (la base debe estar al día antes de generar).
3. `.venv/bin/alembic revision --autogenerate -m "qué cambia"`: compara modelos y base y escribe una
   migración nueva en `migrations/versions/`.
4. **Leer y corregir la migración**: un renombre aparece como borrar + crear (pierde datos; usar
   `op.alter_column(..., new_column_name=...)`), y una columna `NOT NULL` nueva en una tabla con filas
   necesita `server_default` o rellenarla antes.
5. `.venv/bin/alembic upgrade head` y confirmar modelo + migración juntos.

Nunca editar una migración que ya se aplicó en otra base: se escribe una nueva.

| Comando | Para qué |
|---|---|
| `alembic current` | revisión en la que está la base |
| `alembic history` | cadena de migraciones |
| `alembic downgrade -1` | deshacer la última |
| `alembic check` | ¿difieren modelos y base? |
| `alembic upgrade head --sql` | imprimir el SQL sin ejecutarlo |

## Ejecutar

```bash
.venv/bin/uvicorn app.main:app --reload    # documentación interactiva en http://localhost:8000/docs
```

## Simulador de sensores

Sin microcontrolador, `tools/sensor_sim.py` hace de dispositivo: envía lecturas de temperatura y humedad a
`POST /sensors/{id}/readings` con la clave de cada sensor. Los valores cambian de a poco y a veces salen
del rango óptimo (18–24 °C, 70–90 %), así que también sirven para probar las notificaciones.

**1. Dejar corriendo el backend** (con `alembic upgrade head` ya aplicado, ver arriba).

**2. Registrar dos sensores y copiar sus claves.** Cada sensor tiene su propia clave de ingesta, que el
backend **muestra una sola vez**, al crearlo: cópiala en ese momento (si se pierde, se pide otra con
`POST /sensors/{id}/ingest-key` y la anterior deja de servir).

*Opción recomendada, desde el frontend:* iniciar sesión, ir a **Configuración → Mis sensores** y pulsar
**+ Registrar sensor** (uno de temperatura y otro de humedad). El `#` que aparece junto al nombre de cada
sensor es su id; la clave se copia al registrarlo, o con el botón **Clave nueva** de esa fila si ya se
perdió. El sensor aparece como *Conectado* cuando empieza a recibir lecturas, y *Inactivo* si se desactiva.

*Alternativa sin frontend*, desde `http://localhost:8000/docs`: `POST /auth/register` → `POST /auth/login`
→ botón **Authorize** → `POST /sensors` dos veces. O con curl:

```bash
URL=http://localhost:8000
curl -s $URL/auth/register -H 'Content-Type: application/json' \
     -d '{"name":"Profe","email":"profe@example.com","password":"cambiar-esto"}'
TOKEN=$(curl -s $URL/auth/login -d 'username=profe@example.com&password=cambiar-esto' \
     | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s $URL/sensors -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"name":"Temperatura 1","type":"temperature","connection_type":"wifi","reading_interval_minutes":1}'
curl -s $URL/sensors -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"name":"Humedad 1","type":"humidity","connection_type":"wifi","reading_interval_minutes":1}'
```

Cada respuesta trae `"id"` y `"ingest_key"`: anota el par de cada sensor (igual que con el frontend).

**3. Exportar las claves y arrancar.** La clave va en una variable de entorno `SIM_KEY_<id>` (no como
argumento, para que no quede en el historial de la terminal). Con ids 1 (temperatura) y 2 (humedad):

```bash
export SIM_KEY_1=<ingest_key de la temperatura>
export SIM_KEY_2=<ingest_key de la humedad>
.venv/bin/python -m tools.sensor_sim --url http://localhost:8000 \
    --sensor temperature:1 --sensor humidity:2 --demo-segundos 3
```

Imprime una línea por lectura (`201 aceptada`) y se detiene con Ctrl+C. Las variables `export` valen solo
para esa terminal: en otra hay que volver a exportarlas.

| Opción | Para qué |
|---|---|
| `--sensor TIPO:ID` | sensor a simular (`temperature` o `humidity`); se repite una vez por sensor |
| `--demo-segundos N` | espera fija de N segundos entre lecturas; sin ella usa el intervalo del sensor (en minutos) |
| `--semilla N` | repite la misma secuencia de valores en cada ejecución |

Para ver los datos: `GET /sensors/{id}/readings` (historial) y `GET /conditions` (último valor de cada
sensor), con el token del paso 2. Si el simulador imprime `401 Clave de sensor inválida`, esa clave no es
la vigente del sensor y ese sensor se detiene; con `403 Sensor inactivo` reintenta solo.

## Pruebas

```bash
.venv/bin/python -m pytest -q
```

Las pruebas usan `TEST_DB_NAME`, nunca `DB_NAME`: al empezar **borran esa base y la reconstruyen** con las
migraciones, y la vacían después de cada prueba.
