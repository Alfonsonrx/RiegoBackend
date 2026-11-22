# 105 — Simulador de sensores · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. T01–T04 no necesitan backend ni base
(el backend se reemplaza con `httpx.MockTransport`), solo pytest (002 T05). T05 espera a 102 T03 y a
103 T02. La clave de un sensor nunca se pega en un spec, un commit ni un registro: se exporta en la terminal.

## A. Backend
Sin tareas: el simulador usa 103 FR-1 tal como está.

## B. Tests, migrations and tooling
- [x] **T01 — Deriva de valores** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e, FR-2.f · after 002 T05
  `tools/sensor_sim.py`: `TIPOS` y `Deriva` (plan D2); ajustar `sigma` y `k` hasta que pase FR-2.e.
  *Made when:* `.venv/bin/python -m pytest tests -k "105 and fr2" -q` pasa.
- [x] **T02 — Argumentos y claves** · FR-1.b, FR-1.c
  `tools/sensor_sim.py`: `argparse` (`--url`, `--sensor tipo:id`, `--demo-segundos`, `--semilla`) y lectura de `SIM_KEY_<id>` (plan D1).
  *Made when:* `.venv/bin/python -m pytest tests -k "105 and (fr1b or fr1c)" -q` pasa.
- [x] **T03 — Un turno de un sensor** · FR-3.b, FR-3.c, FR-5.a
  `tools/sensor_sim.py`: `paso()` con la tabla de plan D5 y la línea de consola.
  *Made when:* `.venv/bin/python -m pytest tests -k "105 and (fr3b or fr3c or fr5a)" -q` pasa.
- [x] **T04 — El bucle y la salida** · FR-1.a, FR-1.d, FR-3.a, FR-4.a, FR-4.b, FR-4.c, FR-5.b, FR-5.c, FR-5.d, FR-5.e
  `tools/sensor_sim.py`: `correr()` con reloj y `dormir` inyectables (plan D3, D4, D6) y `main()`.
  *Made when:* `.venv/bin/python -m pytest tests -k 105 -q` pasa entero.

— checkpoint: el simulador completo pasa sus pruebas sin backend; `pytest -k 105` verde —

- [ ] **T05 — Uso documentado y corrida real** · FR-1.a, FR-3.a, FR-3.c, FR-4.b · after T04, 102 T03, 103 T02
  `README.md`: sección "Simulador de sensores" (registrar dos sensores con 102, exportar `SIM_KEY_<id>`, arrancar con `--demo-segundos`).
  *Made when:* con `uvicorn app.main:app` corriendo y dos sensores registrados, `.venv/bin/python -m tools.sensor_sim --url http://localhost:8000 --sensor temperature:<id> --sensor humidity:<id> --demo-segundos 3` imprime líneas `201` de ambos sensores cada ~3 s, y `GET /conditions` con el token de la dueña muestra sus últimos valores.
- [ ] **T06 — Borrar el generador anterior** · spec D1, D3 · after T05
  `docs/ScriptTemperatura/`: comprobar que su repositorio no tiene nada sin subir (plan D8) y borrar la carpeta entera, `.git` incluido.
  *Made when:* `git -C docs/ScriptTemperatura status --porcelain` y `git -C docs/ScriptTemperatura log origin/HEAD.. --oneline` salen vacíos antes de borrar, y después `test ! -e docs/ScriptTemperatura` es verdadero.

— checkpoint: lecturas simuladas llegan al backend real; el servidor anterior ya no está en el repositorio —

## C. What could change
Nada pendiente. Protocolo del dispositivo real y otros tipos de sensor: `specs/backlog.md`.

## D. Requirement coverage

| FR | Tasks |
|---|---|
| FR-1 | T02, T04, T05 |
| FR-2 | T01 |
| FR-3 | T03, T04, T05 |
| FR-4 | T04, T05 |
| FR-5 | T03, T04 |

## E. The gates

CI: ninguna definida. Locales: `.venv/bin/python -c "import app.main"` y `.venv/bin/python -m pytest -q`.

## F. Log

- 2026-11-16 · — · spec, plan y tasks escritos (draft) · sin tareas hechas.
- 2026-11-17 · round 1 · base `f70d724` (solo cambios de 105 en el árbol) · modo round.
- 2026-11-17 · T01 · done · 6 pruebas fr2a–f (fallaron: sin `tools`) · `TIPOS` y `deriva()`, un generador en lugar de la clase `Deriva` (plan §1/§2 actualizados); la calibración del plan pasó sin ajustes: 66–78 % dentro de la banda con las semillas 1–5; fr2c compara con tolerancia 1e-9 por el ruido de coma flotante (22.3 − 21.3 = 1.0000000000000018); finish line ok.
- 2026-11-17 · T02 · done · 2 pruebas fr1b (falta `--url`, `--sensor`, `SIM_KEY_3` ausente o vacía, tipo `soil`, id no numérico) y fr1c (`0`, `-5`, `abc`, `nan`, `inf`) (fallaron: sin `main`) · `leer_config()` con `argparse` y mensajes propios en español; salen con código 2 sin ninguna petición; finish line ok.
- 2026-11-17 · T03 · done · 3 pruebas fr3b, fr3c, fr5a sobre `paso()` (fallaron: sin `paso`) · tabla de plan D5 por código de estado; línea de consola con hora, sensor, tipo, valor y resultado; finish line ok.
- 2026-11-17 · T04 · done · 10 pruebas fr1a, fr1d, fr3a, fr4a–c, fr5b–e con backend falso (`httpx.MockTransport`) y reloj falso (fallaron: `correr` no definido) · `correr()` (un hilo, el sensor vivo que toca primero) y `main()` (código 1 sin sensores vivos; Ctrl+C sale con 0); mutación: sin `s.intervalo_s` en la espera rompe 4 pruebas; `pytest -k 105` entero verde (21).
- 2026-11-17 · round 1 · T01–T04 · gates green (import + 122 passed) · `sdd_check` 0 hallazgos, todos los bullets citados · floor: ninguna línea de prueba borrada, sin `skip` ni supresiones · revisión: los prefijos propios de `argparse` ("usage:", "error:", "argument …:") siguen en inglés, el texto de cada mensaje está en español; sin propuestas para §10, sin hallazgos. T05 (README y corrida real) y T06 (borrar `docs/ScriptTemperatura/`) quedan para el round 2.
