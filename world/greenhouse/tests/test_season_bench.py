"""The bench for a DAY: the greenhouse played by its simulator for `HOURS`, a reading every ten minutes, the
grower dosing and heating the bed as the world's physics makes it dry and cool — every pass a deployed agent
runs in a day, one after another on one store, where `test_bench.py` times one pass from a fresh boot. What
it shows that a pass does not: what a store that has lived for a day costs, and the slowest pass of the day
beside the typical one.

Two cases: `day`, the bed alone, two scopes; `framed_day`, the cold frame beside it
(`conftest.framed_greenhouse`), three. Each is held to what the day DID — the pump dosed at least once — and
reports the passes, the whole day's seconds, the median, 95th percentile and slowest pass, the belief base in
quads at the end, the commands sent, and a digest of them: each command's instant, topic and payload. The
digest is what another implementation of the agent must reproduce letter for letter on the same world, so a
comparison of two is of the same day (knowledge/decisions/the-agent-moves-to-rust-one-package-at-a-time.md).
No time is asserted.

**A WALK**, minutes each on the Pi, so `pytest -q` leaves it out and CI runs it; to measure,
`pytest world/greenhouse/tests/test_season_bench.py -s -n0 -m walk`, and `--bench-record` appends a row per
case to `bench/season.tsv`. Its columns are not the pass ledger's, so it is a ledger of its own.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import subprocess
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.runtime import Runtime, boot
from agent.transport.mqtt.driver import Mqtt
from simulation.simulator import Simulator

WORLD = Path(__file__).resolve().parents[1]
BENCH = Path(__file__).parent / "bench"
LEDGER = BENCH / "season.tsv"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"
HOURS = 24
EVERY = timedelta(minutes=10)
COLUMNS = ("date", "commit", "machine", "case", "hours", "passes", "total_s", "median_ms", "p95_ms", "max_ms",
           "quads", "commands", "digest")


class Bus:
    """One broker: what the simulator publishes reaches the grower, and what the grower commands reaches the
    simulator, kept with the instant it was sent."""

    def __init__(self):
        self.runtime = self.simulator = None
        self.commands = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("sensors/"):
            self.runtime.deliver(topic, payload, clock.now())
        else:
            self.commands.append((clock.now().isoformat(), topic, json.loads(payload)))
            self.simulator.command(topic, payload)


def _digest(commands) -> str:
    """The commands of the day, each its instant, topic and payload with sorted keys, hashed."""
    text = "\n".join(json.dumps([at, topic, payload], sort_keys=True) for at, topic, payload in commands)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _commit() -> str:
    try:
        short = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                               check=True, cwd=BENCH).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, check=True, cwd=BENCH).stdout.strip()
        return short + ("-dirty" if dirty else "")
    except Exception:                                               # noqa: BLE001
        return "unknown"


def _record(row: dict) -> None:
    assert not os.environ.get("PYTEST_XDIST_WORKER"), \
        "--bench-record needs -n0: two workers would append to the ledger at once"
    new = not LEDGER.exists()
    with LEDGER.open("a") as out:
        if new:
            out.write("\t".join(COLUMNS) + "\n")
        out.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")


@pytest.mark.walk
@pytest.mark.parametrize("case, framed", [("day", False), ("framed_day", True)])
def test_a_day_in_the_greenhouse_and_what_it_cost(case, framed, monkeypatch, request):
    world = request.getfixturevalue("framed_greenhouse") if framed else WORLD
    now = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: now["at"])
    bus = Bus()
    bus.simulator = Simulator(world, bus, now=NOW)
    bus.runtime = Runtime(boot(world, "grower"), "grower", transport=Mqtt(GH + "grower", bus))
    bus.simulator.open()
    took = []
    while now["at"] < NOW + timedelta(hours=HOURS):
        bus.simulator.step(now["at"])
        started = time.perf_counter()
        bus.runtime.run(passes=1, poll_s=0)
        took.append((time.perf_counter() - started) * 1000)
        now["at"] += EVERY
    quads = len(bus.runtime.beliefs)
    bus.runtime.stop()
    ordered = sorted(took)
    row = {"date": date.today().isoformat(), "commit": _commit(), "machine": platform.node(), "case": case,
           "hours": HOURS, "passes": len(took), "total_s": round(sum(took) / 1000, 1),
           "median_ms": round(statistics.median(took)), "p95_ms": round(ordered[int(0.95 * (len(ordered) - 1))]),
           "max_ms": round(ordered[-1]), "quads": quads, "commands": len(bus.commands), "digest": _digest(bus.commands)}
    print(f"\n{case}: {row['passes']} passes over {HOURS} simulated hours in {row['total_s']} s — median "
          f"{row['median_ms']} ms, p95 {row['p95_ms']}, slowest {row['max_ms']}; {quads} quads at the end, "
          f"{row['commands']} commands, digest {row['digest']}")
    if request.config.getoption("--bench-record"):
        _record(row)
    assert any(topic == "actuators/pump/command" for _, topic, _ in bus.commands), "the bed was dosed in a day"
