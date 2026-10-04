"""The bench for a PASS: the greenhouse's grower, booted from this world, readings delivered, one
`Runtime.run(passes=1, poll_s=0)` — what a deployed agent pays per reading — and the ledger its cost
is tracked in. The search's own bench is `agent/planning/tests/test_bench.py`; this one times the
whole agent around it, sensing and revision and prediction and the executor's walk included.

Four cases, each held to what the pass DID — the commands published, the wants searched and walked,
the intentions ended — and timed as the median of several passes with the LAPS beside it: the
runtime's (`Passed`: the drain of the jobs queued, planning, execution) and the Planner's own
(`Planned`: ground, weigh, derive, search, publish), each lap's median over the runs. No time is
asserted: the machine drifts, and a threshold would be red on a slow morning and say nothing on a
fast one. The clocks are the agent's own events, heard as the metrics part hears them, and nothing
here times a second way.

- `cold_dry_bed`: the thermometer at 12 and the probe at 0.2, both below the bed's ranges, two
  wants in two scopes, the pump's and the heater's commands in one pass;
- `comfortable_bed`: 21 and 0.45, inside — nothing to do, which is the price of a quiet pass;
- `lit_cold_dry_bed`: the cold dry bed with a light on it (`conftest.lit_greenhouse`), a third
  scope and the lamp's command with the other two;
- `dose_and_heating_answered`: the cold dry bed dosed and heated, and the pass eleven minutes
  later in which the readings answer both — on a kept imaginarium, which is what a running agent
  pays once it is warm.

**THE LEDGER.** `pytest world/greenhouse/tests/test_bench.py -s -n0 --bench-record` appends one
row per case to `bench/results.tsv`: the date, the commit (`-dirty` where the tree has uncommitted
changes), the machine, the case, the runs, the median and minimum milliseconds of the pass, every
lap's median in milliseconds, the belief base in quads, the wants searched and the commands sent.
It refuses to be written under xdist, where two workers would append at once. The runbook
`knowledge/runbooks/measure-a-pass.md` says how to read it.
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.runtime import UNFINISHED, Runtime, boot
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
BENCH = Path(__file__).parent / "bench"
LEDGER = BENCH / "results.tsv"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"
RUNS = 5
#  THE RUNTIME'S LAPS, then the Planner's, each `<part>_s` on its event and `<part>_ms` in the ledger.
LAPS = ("drain", "plan", "execute", "ground", "weigh", "derive", "search", "publish")
COLUMNS = ("date", "commit", "machine", "case", "runs", "median_ms", "min_ms", *(f"{lap}_ms" for lap in LAPS),
           "quads", "wants", "commands")

COLD_DRY = {"thermometer": 12.0, "moisture_probe": 0.2}
COMFORTABLE = {"thermometer": 21.0, "moisture_probe": 0.45}


class Broker:
    """What the grower publishes, and nothing else of MQTT."""

    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, json.loads(payload)))


class Clock:
    """One timeline: every read moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


@dataclass
class Pass:
    """One pass: the events that timed it, and what it did."""
    took_ms: float
    laps_ms: dict[str, float]
    quads: int
    wants: int
    commands: list[str]
    walking: int
    ended: list[str]


def _pass(world: Path, monkeypatch, readings: dict, *, before: dict | None = None, later=timedelta(minutes=11)) -> Pass:
    """The grower booted from `world`, `readings` delivered at NOW and one pass run — after a first pass
    over `before`, where given, and `later` on. What the timed pass did, and what the agent's own events
    say it cost: the runtime's `Passed` and the Planner's `Planned`, heard as the metrics part hears them."""
    time = Clock(NOW)
    monkeypatch.setattr(clock, "now", time)
    broker = Broker()
    runtime = Runtime(boot(world, "grower"), "grower", transport=Mqtt(GH + "grower", broker))
    runtime.time = time
    heard: dict = {}
    runtime.passed.connect(lambda event: heard.update(passed=event))
    runtime.parts["planning"].planner.planned.connect(lambda event: heard.update(planned=event))
    runtime.parts["execution"].executor.intention_resolved.connect(lambda event: heard.setdefault("ended", []).append(event.outcome))
    deliver = lambda given: [runtime.deliver(f"sensors/{sensor}/reading", json.dumps({"value": value}).encode(), time.at)
                             for sensor, value in given.items()]
    if before is not None:
        deliver(before)
        assert runtime.run(passes=1, poll_s=0) == UNFINISHED
        time.at = NOW + later
        heard.clear()
    sent = len(broker.published)
    deliver(readings)
    assert runtime.run(passes=1, poll_s=0) == UNFINISHED, "a desire is held, so the agent runs on"
    passed, planned = heard["passed"], heard["planned"]
    laps = {lap: round(getattr(passed, f"{lap}_s", None) or getattr(planned, f"{lap}_s", None) or 0.0, 6) * 1000 for lap in LAPS}
    return Pass(took_ms=passed.duration_s * 1000, laps_ms=laps, quads=passed.quads, wants=planned.wants,
                commands=sorted(topic for topic, _ in broker.published[sent:]),
                walking=len(runtime.parts["execution"].executor.walking()), ended=heard.get("ended", []))


def _commit() -> str:
    """The commit the numbers are about, `-dirty` where the tree is not that commit."""
    try:
        short = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                               check=True, cwd=WORLD).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, check=True, cwd=WORLD).stdout.strip()
        return short + ("-dirty" if dirty else "")
    except Exception:                                               # noqa: BLE001
        return "unknown"


def _record(row: dict) -> None:
    """Append one row to the ledger, writing the header where the file is new."""
    assert not os.environ.get("PYTEST_XDIST_WORKER"), \
        "--bench-record needs -n0: two workers would append to the ledger at once"
    new = not LEDGER.exists()
    BENCH.mkdir(exist_ok=True)
    with LEDGER.open("a") as out:
        if new:
            out.write("\t".join(COLUMNS) + "\n")
        out.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")


HEATER, LAMP, PUMP = "actuators/heater/command", "actuators/lamp/command", "actuators/pump/command"


@pytest.mark.parametrize("case, lit, before, readings, commands, wants, walking, ended", [
    ("cold_dry_bed", False, None, COLD_DRY, [HEATER, PUMP], 2, 2, []),
    ("comfortable_bed", False, None, COMFORTABLE, [], 0, 0, []),
    ("lit_cold_dry_bed", True, None, {**COLD_DRY, "light_sensor": 100}, [HEATER, LAMP, PUMP], 3, 3, []),
    ("dose_and_heating_answered", False, COLD_DRY, COMFORTABLE, [], 0, 0, ["done", "done"]),
])
def test_the_grower_does_what_the_bed_needs_in_one_pass_and_says_what_it_cost(
        case, lit, before, readings, commands, wants, walking, ended, monkeypatch, request):
    world = request.getfixturevalue("lit_greenhouse") if lit else WORLD
    passes = [_pass(world, monkeypatch, readings, before=before) for _ in range(RUNS)]
    #  WHAT THE PASS DID is the same every run, and asserted of the last; what it cost is the median.
    done = passes[-1]
    row = {"date": date.today().isoformat(), "commit": _commit(), "machine": platform.node(), "case": case,
           "runs": RUNS, "median_ms": round(statistics.median(p.took_ms for p in passes)),
           "min_ms": round(min(p.took_ms for p in passes)),
           **{f"{lap}_ms": round(statistics.median(p.laps_ms[lap] for p in passes)) for lap in LAPS},
           "quads": done.quads, "wants": done.wants, "commands": len(done.commands)}
    print(f"\n{case}: median {row['median_ms']} ms of {RUNS} (min {row['min_ms']}) — drain {row['drain_ms']}, "
          f"plan {row['plan_ms']} (ground {row['ground_ms']}, weigh {row['weigh_ms']}, derive {row['derive_ms']}, "
          f"search {row['search_ms']}, publish {row['publish_ms']}), execute {row['execute_ms']}; "
          f"{row['quads']} quads, {row['wants']} want(s) searched, {row['commands']} command(s)")
    if request.config.getoption("--bench-record"):
        _record(row)
    assert done.commands == commands, f"the commands the pass sent: {done.commands}"
    assert (done.wants, done.walking, done.ended) == (wants, walking, ended), \
        f"wants searched, wants walked, intentions ended: {(done.wants, done.walking, done.ended)}"
    assert len({(p.commands == commands, p.wants, p.walking) for p in passes}) == 1, "every run did the same"


def test_the_ledger_has_the_columns_the_bench_writes():
    """A ledger somebody edited by hand, or one an older bench wrote, is read by nobody until
    its header is the bench's."""
    if not LEDGER.exists():
        pytest.skip("no ledger yet — `--bench-record` writes the first row")
    assert LEDGER.read_text().splitlines()[0].split("\t") == list(COLUMNS)
