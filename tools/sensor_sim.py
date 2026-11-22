"""Simulador de sensores (spec 105): envía lecturas a la recepción de 103 igual que el dispositivo real.

    export SIM_KEY_4=…   # clave de ingesta del sensor 4, nunca en la línea de órdenes
    .venv/bin/python -m tools.sensor_sim --url http://localhost:8000 --sensor temperature:4 [--demo-segundos 5]
"""
import argparse
import math
import os
import random
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime

import httpx

# Hard limits, optimal band and drift calibration per type (plan D2).
# ponytail: sigma and k tuned by hand; measure them from a real sensor once one exists.
TIPOS = {
    "temperature": {"min": -1, "max": 30, "banda": (18, 24), "paso_max": 1.0, "sigma": 0.4, "k": 0.01},
    "humidity": {"min": 0, "max": 100, "banda": (70, 90), "paso_max": 3.0, "sigma": 1.2, "k": 0.008},
}
ESPERA_SIN_INTERVALO_S = 60  # until the backend has accepted a reading and said its interval (FR-4.c)
TIEMPO_PETICION_S = 10


def deriva(tipo, rng: random.Random):
    """A sensor's values: the first inside the band, each a small step from the previous one,
    pulled back toward the band's centre (FR-2, plan D2)."""
    t = TIPOS[tipo]
    lo, hi = t["banda"]
    centro = (lo + hi) / 2
    x = round(rng.uniform(lo, hi), 1)
    while True:
        yield x
        nuevo = x + t["k"] * (centro - x) + rng.gauss(0, t["sigma"])
        x = round(min(max(nuevo, x - t["paso_max"], t["min"]), x + t["paso_max"], t["max"]), 1)


@dataclass
class Sensor:
    id: int
    tipo: str
    clave: str = field(repr=False)  # the ingest key: never printed, not even by repr (FR-1.d)
    valores: Iterator[float] = field(repr=False)
    intervalo_s: float | None = None  # last accepted interval; None until the backend accepts one
    proximo: float = 0.0  # monotonic moment of its next reading
    detenido: bool = False  # True after an invalid key (FR-5.a)


def _sensor(texto: str) -> tuple[str, int]:
    tipo, _, ident = texto.partition(":")
    if tipo not in TIPOS:
        raise argparse.ArgumentTypeError(f"tipo desconocido: {tipo} (usa {' o '.join(TIPOS)})")
    if not ident.isdigit():
        raise argparse.ArgumentTypeError(f"id inválido en {texto}: usa tipo:id, p. ej. humidity:3")
    return tipo, int(ident)


def _segundos(texto: str) -> float:
    try:
        s = float(texto)
    except ValueError:
        s = math.nan
    if not (math.isfinite(s) and s > 0):
        raise argparse.ArgumentTypeError(f"debe ser un número de segundos mayor que cero, no {texto}")
    return s


def leer_config(argv, env) -> tuple[str, list[Sensor], float | None]:
    """URL, sensors and demo interval; a bad or incomplete config exits with code 2 before any send (FR-1.b, c)."""
    p = argparse.ArgumentParser(prog="python -m tools.sensor_sim",
                                description="Envía lecturas simuladas a la recepción de lecturas del backend.")
    p.add_argument("--url", help="dirección del backend, p. ej. http://localhost:8000")
    p.add_argument("--sensor", action="append", type=_sensor, default=[], metavar="TIPO:ID",
                   help="sensor registrado (temperature o humidity) y su id; repetible. Clave en SIM_KEY_<id>")
    p.add_argument("--demo-segundos", type=_segundos, help="espera fija entre lecturas, en lugar del intervalo")
    p.add_argument("--semilla", type=int, help="repite la misma secuencia de valores en cada ejecución")
    a = p.parse_args(argv)
    if not a.url:
        p.error("falta --url")
    if not a.sensor:
        p.error("falta al menos un --sensor TIPO:ID")
    sensores = []
    for tipo, ident in a.sensor:
        clave = env.get(f"SIM_KEY_{ident}")  # from the environment, never the command line (plan D1)
        if not clave:
            p.error(f"falta SIM_KEY_{ident}: exporta la clave de ingesta del sensor {ident}")
        rng = random.Random(None if a.semilla is None else f"{a.semilla}-{ident}")
        sensores.append(Sensor(ident, tipo, clave, deriva(tipo, rng)))
    return a.url.rstrip("/"), sensores, a.demo_segundos


def paso(cliente: httpx.Client, url: str, s: Sensor) -> None:
    """One turn of one sensor: send its next value with its key and act on the answer (FR-3.b, c; plan D5).
    Decides by status code: 103 plan §3 fixes 401 for an invalid key and 403 for an inactive sensor."""
    valor = next(s.valores)
    try:
        r = cliente.post(f"{url}/sensors/{s.id}/readings", json={"value": valor},
                         headers={"X-Sensor-Key": s.clave})  # the key goes only in this header (plan D7)
    except httpx.TransportError as e:
        resultado = f"sin respuesta ({type(e).__name__}): se reintenta"  # FR-5.c
    else:
        if r.status_code == 201:
            s.intervalo_s = r.json()["reading_interval_minutes"] * 60
            resultado = f"201 aceptada, intervalo {r.json()['reading_interval_minutes']} min"
        elif r.status_code == 401:
            s.detenido = True
            resultado = f"401 Clave de sensor inválida: sensor {s.id} detenido"  # FR-5.a
        elif r.status_code == 403:
            resultado = "403 Sensor inactivo: se reintenta"  # FR-5.b
        else:
            resultado = f"{r.status_code}: se reintenta"  # 5xx (FR-5.c); another 4xx should not happen
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} · sensor {s.id} ({s.tipo}) · {valor} · {resultado}", flush=True)


def correr(cliente, url, sensores, demo, reloj, dormir) -> None:
    """One thread, one turn per sensor (plan D3): wait for the live sensor due first, run its turn, repeat.
    Returns when no sensor is live. `reloj` and `dormir` are parameters so tests move time without waiting."""
    inicio = reloj()
    for s in sensores:
        s.proximo = inicio  # each sensor's first reading goes out at once (FR-3.a)
    while vivos := [s for s in sensores if not s.detenido]:
        s = min(vivos, key=lambda v: v.proximo)
        espera = s.proximo - reloj()
        if espera > 0:
            dormir(espera)
        paso(cliente, url, s)
        s.proximo = reloj() + (demo or s.intervalo_s or ESPERA_SIN_INTERVALO_S)  # plan D4 (FR-4, FR-5.b, c)


def main(argv=None, env=None, cliente=None, reloj=time.monotonic, dormir=time.sleep) -> int:
    url, sensores, demo = leer_config(argv, os.environ if env is None else env)
    with cliente or httpx.Client(timeout=TIEMPO_PETICION_S) as c:
        try:
            correr(c, url, sensores, demo, reloj, dormir)
        except KeyboardInterrupt:
            print("Simulador detenido.")
            return 0
    print("Todos los sensores están detenidos: revisa sus claves.", file=sys.stderr)
    return 1  # no live sensors left (FR-5.e, plan D6)


if __name__ == "__main__":
    sys.exit(main())
