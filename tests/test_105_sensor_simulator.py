import random
import re

import httpx

from tools import sensor_sim
from tools.sensor_sim import TIPOS, deriva

LIMITES = {"temperature": (-1, 30), "humidity": (0, 100)}
PASO = {"temperature": 1.0, "humidity": 3.0}
KEYS = {"SIM_KEY_4": "k4-secreta", "SIM_KEY_3": "k3-secreta"}


class Fin(Exception):
    """Raised by the fake sleep to end a run that would otherwise go on forever."""


def ok(minutes=60):
    return httpx.Response(201, json={"id": 1, "sensor_id": 0, "value": 0, "recorded_at": "2026-11-17T12:00:00Z",
                                     "reading_interval_minutes": minutes})


def run(answer, *argv, env=KEYS, until=10_000, url="http://backend"):
    """main() against a fake backend and a fake clock, without waiting.
    `answer(sensor_id, n)` gives the n-th (1-based) response for that sensor: an httpx.Response or an exception.
    Returns (exit code or None if stopped by the clock, [(sensor_id, clock, request, sleeps so far)], [sleeps])."""
    clock, sent, slept = [0.0], [], []

    def backend(request):
        sid = int(request.url.path.split("/")[2])
        sent.append((sid, clock[0], request, len(slept)))  # len(slept): sleeps before this send
        r = answer(sid, sum(1 for s, *_ in sent if s == sid))
        if isinstance(r, Exception):
            raise r
        return r

    def sleep(seconds):
        slept.append(seconds)
        clock[0] += seconds
        if clock[0] > until:
            raise Fin

    client = httpx.Client(transport=httpx.MockTransport(backend))
    try:
        code = sensor_sim.main([*(["--url", url] if url else []), *argv], env=env, cliente=client,
                               reloj=lambda: clock[0], dormir=sleep)
    except Fin:
        code = None
    except SystemExit as e:
        code = e.code
    return code, sent, slept


def times(sent, sensor_id):
    return [t for s, t, *_ in sent if s == sensor_id]


def valores(tipo, n=10_000, semilla=1):
    serie = deriva(tipo, random.Random(semilla))
    return [next(serie) for _ in range(n)]


def en_banda(tipo, v):
    lo, hi = TIPOS[tipo]["banda"]
    return lo <= v <= hi


# FR-2 — Valores que derivan

def test_105_fr2a_values_within_hard_limits():
    for tipo, (lo, hi) in LIMITES.items():
        assert all(lo <= v <= hi for v in valores(tipo)), tipo


def test_105_fr2b_at_most_one_decimal():
    for tipo in LIMITES:
        assert all(round(v, 1) == v for v in valores(tipo)), tipo


def test_105_fr2c_small_steps_from_previous_value():
    for tipo in LIMITES:
        serie = valores(tipo)
        worst = max(abs(b - a) for a, b in zip(serie, serie[1:]))
        assert worst <= PASO[tipo] + 1e-9, (tipo, worst)  # float noise only: 22.3 - 21.3 is 1.0000000000000018


def test_105_fr2d_first_value_inside_band():
    for tipo in LIMITES:
        assert all(en_banda(tipo, next(deriva(tipo, random.Random(s)))) for s in range(100)), tipo


def test_105_fr2e_mostly_inside_band_but_leaves_it():
    for tipo in LIMITES:
        dentro = sum(en_banda(tipo, v) for v in valores(tipo)) / 10_000
        assert 0.60 <= dentro <= 0.85 and dentro < 1, (tipo, dentro)


def test_105_fr2f_seed_repeats_sequence():
    for tipo in LIMITES:
        assert valores(tipo, 50, semilla=7) == valores(tipo, 50, semilla=7)
        assert valores(tipo, 50, semilla=None) != valores(tipo, 50, semilla=None)


# FR-1 — Configuración de los sensores simulados

def test_105_fr1b_incomplete_config_exits_naming_what_is_missing(capsys):
    cases = {
        "--url": (["--sensor", "temperature:4"], KEYS, None),
        "--sensor": ([], KEYS, "http://backend"),
        "SIM_KEY_3": (["--sensor", "humidity:3"], {"SIM_KEY_4": "k4"}, "http://backend"),
        "SIM_KEY_3 ": (["--sensor", "humidity:3"], {"SIM_KEY_3": ""}, "http://backend"),  # empty = missing
        "soil": (["--sensor", "soil:3"], KEYS, "http://backend"),
        "humidity:tres": (["--sensor", "humidity:tres"], KEYS, "http://backend"),
    }
    for named, (argv, env, url) in cases.items():
        code, sent, _ = run(lambda *_: ok(), *argv, env=env, url=url)
        assert code not in (0, None) and sent == [], named
        assert named.strip() in capsys.readouterr().err, named


def one_turn(response, sensor_id=4, tipo="temperature"):
    """paso() for one sensor against a backend that gives `response`; returns (sensor, requests)."""
    sent = []

    def backend(request):
        sent.append(request)
        if isinstance(response, Exception):
            raise response
        return response

    s = sensor_sim.Sensor(sensor_id, tipo, f"k{sensor_id}-secreta", deriva(tipo, random.Random(1)))
    sensor_sim.paso(httpx.Client(transport=httpx.MockTransport(backend)), "http://backend", s)
    return s, sent


# FR-3 — Enviar cada lectura

def test_105_fr3b_sends_value_with_that_sensors_key():
    _, [request] = one_turn(ok())
    assert (request.method, str(request.url)) == ("POST", "http://backend/sensors/4/readings")
    assert request.headers["X-Sensor-Key"] == "k4-secreta"
    body = httpx.Response(200, content=request.content).json()
    assert list(body) == ["value"] and -1 <= body["value"] <= 30


def test_105_fr3c_console_line_per_send(capsys):
    _, [request] = one_turn(ok(15))
    value = httpx.Response(200, content=request.content).json()["value"]
    line = capsys.readouterr().out.strip()
    assert re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d · sensor 4 \(temperature\) · ", line), line
    assert f" · {value} · 201" in line, line


# FR-5 — Rechazos y caídas

def test_105_fr5a_invalid_key_stops_that_sensor(capsys):
    s, _ = one_turn(httpx.Response(401, json={"detail": "Clave de sensor inválida"}), sensor_id=3)
    assert s.detenido
    assert "sensor 3" in capsys.readouterr().out


def test_105_fr1c_demo_interval_must_be_seconds_above_zero(capsys):
    for bad in ("0", "-5", "abc", "nan", "inf"):
        code, sent, _ = run(lambda *_: ok(), "--sensor", "temperature:4", "--demo-segundos", bad)
        assert code not in (0, None) and sent == [], bad
        assert "--demo-segundos" in capsys.readouterr().err, bad


# The whole run: main() and its loop

BOTH = ("--sensor", "temperature:4", "--sensor", "humidity:3")
REFUSED = httpx.Response(401, json={"detail": "Clave de sensor inválida"})
INACTIVE = httpx.Response(403, json={"detail": "Sensor inactivo"})


def in_turn(*answers):
    """The n-th request gets answers[n-1]; the last one repeats."""
    return lambda sid, n: answers[min(n, len(answers)) - 1]


def test_105_fr1a_sends_readings_of_each_configured_sensor():
    _, sent, _ = run(in_turn(ok(1)), *BOTH, until=200)
    paths = {str(r.url) for *_, r, _ in sent}
    assert paths == {"http://backend/sensors/4/readings", "http://backend/sensors/3/readings"}


def test_105_fr1d_key_never_on_the_console(capsys):
    code, sent, _ = run(in_turn(ok(1), httpx.ConnectError("sin red"), INACTIVE, REFUSED), "--sensor", "temperature:4")
    out = capsys.readouterr()
    assert (code, len(sent)) == (1, 4)
    assert "k4-secreta" not in out.out + out.err


def test_105_fr3a_first_reading_of_each_sensor_at_start():
    _, sent, _ = run(in_turn(ok(1)), *BOTH, until=200)
    assert [(sid, sleeps) for sid, _, _, sleeps in sent[:2]] == [(4, 0), (3, 0)]


def test_105_fr4a_waits_the_interval_the_backend_returned():
    _, sent, _ = run(in_turn(ok(2), ok(5)), "--sensor", "temperature:4", until=500)
    assert times(sent, 4)[:3] == [0, 120, 420]


def test_105_fr4b_demo_seconds_replace_the_interval():
    _, sent, _ = run(in_turn(ok(60)), "--sensor", "temperature:4", "--demo-segundos", "3", until=10)
    assert times(sent, 4)[:4] == [0, 3, 6, 9]
    _, sent, _ = run(in_turn(ok(60)), "--sensor", "temperature:4", until=7200)
    assert times(sent, 4)[:3] == [0, 3600, 7200]


def test_105_fr4c_60_seconds_until_the_first_acceptance():
    _, sent, _ = run(in_turn(httpx.ConnectError("sin red")), "--sensor", "temperature:4", until=150)
    assert times(sent, 4)[:3] == [0, 60, 120]


def test_105_fr5b_inactive_sensor_retried_after_its_interval():
    _, sent, _ = run(in_turn(ok(2), INACTIVE, INACTIVE, ok(2)), "--sensor", "temperature:4", until=400)
    assert times(sent, 4)[:4] == [0, 120, 240, 360]


def test_105_fr5c_backend_down_retried_without_ending():
    code, sent, _ = run(in_turn(ok(2), httpx.Response(503), httpx.ConnectError("sin red"), ok(2)),
                        "--sensor", "temperature:4", until=400)
    assert code is None  # still running when the fake clock stopped it
    assert times(sent, 4)[:4] == [0, 120, 240, 360]


def test_105_fr5d_other_sensors_go_on_after_one_stops():
    _, sent, _ = run(lambda sid, n: REFUSED if sid == 3 else ok(1), *BOTH, until=200)
    assert (len(times(sent, 3)), len(times(sent, 4)) >= 3) == (1, True)


def test_105_fr5e_exits_with_error_when_every_sensor_stopped():
    code, _, _ = run(in_turn(REFUSED), *BOTH)
    assert code == 1
