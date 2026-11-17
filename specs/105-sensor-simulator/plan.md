# 105 — Simulador de sensores · Implementation plan

Status: draft · Spec: `spec.md` · Reference: `specs/sdd.profile.md`

## 1. Module structure

### A. Backend (`app/`)
Sin cambios: el simulador usa `POST /sensors/{sensor_id}/readings` de 103 tal como está.

### B. Tests, migrations and tooling
| File | Holds | FR |
|---|---|---|
| `tools/sensor_sim.py` | todo el simulador: argumentos, `TIPOS` (límites y calibración por tipo), `Deriva`, `paso()` (un turno de un sensor), `correr()` (el bucle), `main()` | FR-1–FR-5 |
| `tests/test_105_sensor_simulator.py` | plan §5, con `httpx.MockTransport` en lugar del backend y un reloj falso | FR-1–FR-5 |
| `README.md` | sección "Simulador de sensores": cómo registrar dos sensores, exportar las claves y arrancarlo | FR-1 |
| `docs/ScriptTemperatura/` | se borra entero (servidor, estado, generador y su `.git` anidado) una vez copiado lo que sirve | D3 del spec |

Un solo archivo: el simulador son ~100 líneas y nada fuera de él las reutiliza. Sin `numpy`: la deriva
usa `random` de la biblioteca estándar. `httpx` ya está en `requirements.txt`; no se añade ninguna
dependencia.

## 2. Data model

El simulador no guarda nada. Estado en memoria por sensor:

| Campo | Tipo | Significado |
|---|---|---|
| `id` | int | id del sensor en el backend |
| `tipo` | `"temperature"` \| `"humidity"` | clave de `TIPOS` |
| `clave` | str | clave de ingesta, leída de `SIM_KEY_<id>`; nunca se imprime |
| `deriva` | `Deriva` | valor actual y generador de números |
| `intervalo_s` | float \| None | último `reading_interval_minutes × 60` aceptado; `None` hasta la primera aceptación |
| `proximo` | float | momento (reloj monotónico) de su siguiente lectura |
| `detenido` | bool | `True` tras una clave inválida |

`TIPOS` (calibración; los valores de `sigma` y `k` se ajustan en T02 hasta cumplir FR-2.e):

```json
{ "temperature": { "min": -1, "max": 30, "banda": [18, 24], "paso_max": 1.0, "sigma": 0.4, "k": 0.01 },
  "humidity":    { "min": 0,  "max": 100, "banda": [70, 90], "paso_max": 3.0, "sigma": 1.2, "k": 0.008 } }
```

Arranque:

```sh
export SIM_KEY_4=…   # clave del sensor 4 (102 FR-1.b), nunca en la línea de órdenes
export SIM_KEY_3=…
.venv/bin/python -m tools.sensor_sim --url http://localhost:8000 \
    --sensor temperature:4 --sensor humidity:3 [--demo-segundos 5] [--semilla 1]
```

Envío (igual que el dispositivo, 103 plan §2): `POST {url}/sensors/4/readings`, cabecera
`X-Sensor-Key`, cuerpo `{"value": 21.3}`.

Línea de consola (FR-3.c):

```
2026-11-16 13:00:02 · sensor 4 (temperature) · 21.3 · 201 aceptada, próxima en 60 min
2026-11-16 13:00:02 · sensor 3 (humidity) · 81.0 · 401 Clave de sensor inválida: sensor detenido
```

## 3. Surface

Ninguna ruta nueva. El simulador consume una:

| Método y ruta | Autenticación | Uso | FR |
|---|---|---|---|
| `POST /sensors/{sensor_id}/readings` (103) | cabecera `X-Sensor-Key` | una lectura por turno | FR-3, FR-4, FR-5 |

Línea de órdenes: `--url` (obligatorio), `--sensor tipo:id` (repetible, al menos uno), `--demo-segundos`
(opcional, > 0), `--semilla` (opcional, entero). Claves: variable de entorno `SIM_KEY_<id>` por sensor.

## 4. Technical decisions

**D1 — Argumentos con `argparse` para lo que no es secreto; la clave por `SIM_KEY_<id>`.** `argparse` da la ayuda y los errores de uso gratis; un error de configuración sale con código 2 y un mensaje que nombra el dato (`falta SIM_KEY_4`, `tipo desconocido: soil`). *Discarded:* la clave como argumento (queda en el historial del shell y en `ps`, NFR Security); un archivo de configuración (un archivo más para dos o tres valores). (FR-1.a–c)

**D2 — Deriva con vuelta a la banda: `x ← x + k·(centro − x) + gauss(0, sigma)`, recortado a `±paso_max` del anterior, luego a `[min, max]`, luego redondeado a un decimal.** Partiendo de un valor de un decimal, recortar a `±paso_max` y redondear no puede pasarse del paso, porque los extremos ya caen en la grilla de décimas. El primer valor es uniforme dentro de la banda. Con `k` pequeño la desviación estable es `sigma / √(2k)` ≈ 2,9 °C y 9,5 %, lo que deja ~70 % dentro de la banda (D2 del spec). `# ponytail: sigma y k a mano por tipo; medirlos de un sensor real cuando exista`. *Discarded:* `numpy.random.choice` del generador original (valores independientes, spec D2). (FR-2.a–f)

**D3 — Un solo hilo con un turno por sensor.** `correr()` elige el sensor no detenido con menor `proximo`, duerme hasta ese momento, llama a `paso()` y repite. Reloj y `sleep` son parámetros, para que las pruebas avancen el tiempo sin esperar. *Discarded:* un hilo o una tarea `asyncio` por sensor (sincronización para nada; con pocos sensores un turno de red de milisegundos no atrasa a los demás). (FR-3.a–b, FR-4.a, FR-5.d)

**D4 — Espera tras cada turno: `--demo-segundos` si se dio; si no, `intervalo_s` si hubo alguna aceptación; si no, 60 s.** `intervalo_s` se actualiza con cada 201, así que un cambio de la persona se aplica desde la respuesta siguiente. (FR-4.a–c, FR-5.b–c)

**D5 — Qué hace `paso()` con cada respuesta:**

| Respuesta | Efecto |
|---|---|
| 201 | `intervalo_s ← reading_interval_minutes × 60`; línea "aceptada" |
| 401 | `detenido ← True`; línea "Clave de sensor inválida: sensor detenido" |
| 403 | reintento tras D4; línea "Sensor inactivo" |
| 5xx o `httpx.TransportError` (sin conexión, tiempo agotado) | reintento tras D4; línea con el error |
| otro 4xx (p. ej. 422) | reintento tras D4; línea con el código. No debería pasar: el valor ya cumple 103 FR-1.e |

Se decide por código, no por texto: 103 plan §3 fija 401 y 403 para esos dos mensajes. Tiempo de espera
de cada petición: 10 s. (FR-5.a–c)

**D6 — Sin sensores vivos, `correr()` devuelve y `main()` sale con código 1.** (FR-5.e)

**D7 — La clave solo va en la cabecera.** Ninguna línea de consola ni mensaje de error la incluye; `httpx` no registra cabeceras y el simulador no configura `logging`. La prueba de FR-1.d captura toda la salida de una corrida con 201, 401, 403 y error de red y busca la clave. (FR-1.d)

**D8 — Se borra `docs/ScriptTemperatura/`.** Antes, comprobar que su repositorio no tiene cambios sin subir a su remoto (`git status` limpio y `git log origin/HEAD..` vacío dentro de la carpeta); su historia queda allí. (spec D1, D3)

## 5. Test strategy

`tests/test_105_sensor_simulator.py`, sin base de datos ni backend: `httpx.Client(transport=httpx.MockTransport(f))`
donde `f` registra cada petición y responde lo que pida la prueba; reloj falso (`ahora` en una lista) y
`dormir` que avanza ese reloj. `capsys` captura la consola.

| Bullet | Caso (Given / When / Then) | Kind |
|---|---|---|
| FR-1.a | Given `--url`, `--sensor temperature:4 --sensor humidity:3` y ambas claves / When arranca y corre un ciclo / Then hay una petición a `/sensors/4/readings` y otra a `/sensors/3/readings` | event |
| FR-1.b | Given sin `--url`; sin `--sensor`; `SIM_KEY_3` ausente; `--sensor soil:3` / When arranca / Then sale con código distinto de 0, el mensaje nombra el dato y el transporte no recibió ninguna petición | negative |
| FR-1.c | Given `--demo-segundos 0`, `-5` y `abc` / When arranca / Then sale con código distinto de 0 y sin peticiones | negative |
| FR-1.d | Given una clave conocida y respuestas 201, 401, 403 y `ConnectError` / When corre / Then la clave no aparece en `stdout` ni `stderr` | positive |
| FR-2.a | Given `Deriva` de cada tipo con semilla 1 / When genera 10 000 valores / Then todos están en `[-1, 30]` y `[0, 100]` | positive |
| FR-2.b | Given esos valores / Then `round(v, 1) == v` en todos | positive |
| FR-2.c | Given esos valores / Then cada par seguido difiere a lo sumo 1,0 (temperatura) y 3,0 (humedad) | positive |
| FR-2.d | Given 100 semillas distintas / When se toma el primer valor de cada tipo / Then todos están en su banda | positive |
| FR-2.e | Given 10 000 valores con semilla 1 / Then la fracción dentro de la banda está entre 0,60 y 0,85 y al menos uno está fuera | event |
| FR-2.f | Given semilla 7 dos veces y sin semilla dos veces / When se generan 50 valores / Then con semilla las secuencias son iguales; sin semilla, distintas | both sides |
| FR-3.a | Given dos sensores / When arranca, antes de ningún `dormir` / Then ya se envió una lectura de cada uno | event |
| FR-3.b | Given el sensor 4 con clave `k4` / When le toca / Then la petición lleva `X-Sensor-Key: k4` y un cuerpo `{"value": v}` con `v` en sus límites | event |
| FR-3.c | Given un envío aceptado / When termina / Then la consola tiene una línea con hora, `sensor 4`, `temperature`, el valor y `201` | event |
| FR-4.a | Given respuesta 201 con `reading_interval_minutes` 2 y luego 5 / When corre / Then la segunda lectura sale 120 s después de la primera y la tercera 300 s después de la segunda | event |
| FR-4.b | Given `--demo-segundos 3` y respuesta con intervalo 60 / When corre / Then las lecturas salen cada 3 s; sin `--demo-segundos`, cada 3600 s | both sides |
| FR-4.c | Given respuestas `ConnectError` desde el arranque / When corre / Then los intentos salen cada 60 s | state |
| FR-5.a | Given respuesta 401 para el sensor 3 / When le toca / Then no hay más peticiones a `/sensors/3/readings` y la consola nombra al sensor 3 | negative |
| FR-5.b | Given 201 con intervalo 1 y luego 403, 403, 201 / When corre / Then hay cuatro peticiones a 60 s una de otra | negative |
| FR-5.c | Given 201 con intervalo 1 y luego 503 y `ConnectError` / When corre / Then reintenta a los 60 s cada vez y no termina | negative |
| FR-5.d | Given el sensor 3 responde 401 y el 4 responde 201 / When corren tres ciclos / Then el 4 sigue recibiendo peticiones | state |
| FR-5.e | Given todos los sensores responden 401 / When corre / Then `main()` sale con código 1 | negative |

## 6. Build order

1. `Deriva` y `TIPOS`, con sus pruebas (FR-2); ajustar `sigma` y `k`.
2. Argumentos y lectura de claves (FR-1.a–c).
3. `paso()` con la tabla de D5 y la línea de consola (FR-3.b–c, FR-5.a–c).
4. `correr()` y `main()` (FR-3.a, FR-4, FR-5.d–e, FR-1.d).
5. Sección del README; prueba a mano contra el backend cuando 102 y 103 estén construidos.
6. Borrar `docs/ScriptTemperatura/` (D8).

## 7. Requirement coverage

| FR | Plan sections |
|---|---|
| FR-1 | §1, §2, §3, §4 D1 D7, §5 |
| FR-2 | §2, §4 D2, §5 |
| FR-3 | §2, §3, §4 D3, §5 |
| FR-4 | §4 D3 D4, §5 |
| FR-5 | §4 D3 D5 D6, §5 |
