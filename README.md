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

## Pruebas

```bash
.venv/bin/python -m pytest -q
```

Las pruebas usan `TEST_DB_NAME`, nunca `DB_NAME`: al empezar **borran esa base y la reconstruyen** con las
migraciones, y la vacían después de cada prueba.
