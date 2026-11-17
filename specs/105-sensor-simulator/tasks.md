# 105 — Simulador de sensores · Tasks

Status: draft · Spec: `spec.md` · Plan: `plan.md`

Cada tarea escribe primero su prueba (plan §5) y luego el código. T01–T04 no necesitan backend ni base
(el backend se reemplaza con `httpx.MockTransport`), solo pytest (002 T05). T05 espera a 102 T03 y a
103 T02. La clave de un sensor nunca se pega en un spec, un commit ni un registro: se exporta en la terminal.

## A. Backend
Sin tareas: el simulador usa 103 FR-1 tal como está.

## B. Tests, migrations and tooling
- [ ] **T01 — Deriva de valores** · FR-2.a, FR-2.b, FR-2.c, FR-2.d, FR-2.e, FR-2.f · after 002 T05
  `tools/sensor_sim.py`: `TIPOS` y `Deriva` (plan D2); ajustar `sigma` y `k` hasta que pase FR-2.e.
  *Made when:* `.venv/bin/python -m pytest tests -k "105 and fr2" -q` pasa.
- [ ] **T02 — Argumentos y claves** · FR-1.b, FR-1.c
  `tools/sensor_sim.py`: `argparse` (`--url`, `--sensor tipo:id`, `--demo-segundos`, `--semilla`) y lectura de `SIM_KEY_<id>` (plan D1).
  *Made when:* `.venv/bin/python -m pytest tests -k "105 and (fr1b or fr1c)" -q` pasa.
- [ ] **T03 — Un turno de un sensor** · FR-3.b, FR-3.c, FR-5.a
  `tools/sensor_sim.py`: `paso()` con la tabla de plan D5 y la línea de consola.
  *Made when:* `.venv/bin/python -m pytest tests -k "105 and (fr3b or fr3c or fr5a)" -q` pasa.
- [ ] **T04 — El bucle y la salida** · FR-1.a, FR-1.d, FR-3.a, FR-4.a, FR-4.b, FR-4.c, FR-5.b, FR-5.c, FR-5.d, FR-5.e
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
