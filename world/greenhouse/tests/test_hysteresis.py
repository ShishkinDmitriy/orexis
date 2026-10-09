"""The greenhouse's hysteresis (#944): a want is minted where a reading leaves the bed's operating
range and reached only back inside the narrower range the bed states, so a reading straying across a
floor on its noise mints one want and withdraws none until it clears.

Each case runs the grower twice where the contrast is the point: on the world as it is, and on the
world stating no narrower range — its desire's one test the one every shipped desire had before,
no reading below any range the bed states — which is the guard: the same readings there mint a want
per crossing and withdraw it per crossing back.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import rdflib

from agent import clock
from agent.runtime import Runtime, boot
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"
SOIL = "sensors/moisture_probe/reading"


class Broker:
    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, json.loads(payload)))


def _world(tmp_path: Path, *, narrower: bool = True, pump: bool = True) -> Path:
    """The greenhouse, copied — as it is, or stating no narrower range and its desire minting and
    reached by the one test, or with a grower that holds no pump, so a dry bed stands unrepaired and
    a want's life is told by the readings alone."""
    world = tmp_path / "world" / "greenhouse"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / "domains").symlink_to(WORLD.parents[1] / "domains")
    if not narrower:
        text = (world / "world.ttl").read_text()
        assert " ;\n    orexis:hasNarrowerRange :bed_narrower ." in text
        (world / "world.ttl").write_text(text.replace(" ;\n    orexis:hasNarrowerRange :bed_narrower .", " ."))
        desires = (world / "desires.ttl").read_text()
        said = "planning:metWhen :comfortable ;\n    planning:reachedWhen :comfortable_again ."
        assert said in desires
        (world / "desires.ttl").write_text(desires.replace(said, "planning:metWhen :comfortable_again ."))
    if not pump:
        society = (world / "society.ttl").read_text()
        assert "actuation:hasActuator :pump , :heater ." in society
        (world / "society.ttl").write_text(society.replace("actuation:hasActuator :pump , :heater .",
                                                           "actuation:hasActuator :heater ."))
    return world


def _grower(world: Path):
    broker = Broker()
    return Runtime(boot(world, "grower"), "grower", transport=Mqtt(GH + "grower", broker)), broker


def _life(caplog) -> list[tuple[str, str]]:
    """What happened to the soil's want, in order: minted, or withdrawn and why — once per pass, the
    beliefs' withdrawal beside the imaginarium's being the same act said twice."""
    out = []
    for r in caplog.records:
        said = r.getMessage()
        if r.name == "derive_wants" and "pursuing" in said and "SoilMoisture" in said:
            out.append(("minted", ""))
        found = re.match(r".*SoilMoisture withdrawn: (.*)$", said) if r.name == "withdraw" else None
        if found and (not out or out[-1] != ("withdrawn", found.group(1))):
            out.append(("withdrawn", found.group(1)))
    return out


#  EVERY NARROWER RANGE THE BED STATES, with the operating range it lies inside for the same property.
_NARROWER_Q = """
PREFIX orexis: <http://example.org/orexis#>
PREFIX ssn: <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>
SELECT ?subject ?property ?lo ?hi ?nlo ?nhi WHERE {
  ?subject orexis:hasNarrowerRange/ssn-system:inCondition ?n .
  ?n ssn:forProperty ?property ; schema:minValue ?nlo ; schema:maxValue ?nhi .
  OPTIONAL { ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?c .
             ?c ssn:forProperty ?property ; schema:minValue ?lo ; schema:maxValue ?hi } }"""


def test_the_narrower_range_lies_inside_the_operating_range_and_holds_its_middle():
    """Both of the bed's: soil and air. Inside, or it is no narrower; holding the middle, since the
    dose and the heating aim there, and a step sized to a middle outside it would land where its want
    reads unreached — a plan that never ends."""
    found = list(rdflib.Graph().parse(WORLD / "world.ttl").query(_NARROWER_Q))
    assert len(found) == 2, found
    for r in found:
        assert r.lo is not None, f"{r.property}: a narrower range with no operating range to narrow"
        lo, hi, nlo, nhi = (float(v) for v in (r.lo, r.hi, r.nlo, r.nhi))
        assert lo < nlo < (lo + hi) / 2 < nhi < hi, (r.property, lo, nlo, nhi, hi)


#  ACROSS THE FLOOR OF 0.30 BY A TEN-THOUSANDTH EACH WAY, AND THEN CLEAR OF THE NARROWER ONE OF 0.3002.
STRAYING = [0.3001, 0.2999, 0.3001, 0.2999, 0.3001, 0.2999, 0.3003]


@pytest.mark.parametrize("narrower", [True, False], ids=["narrower", "none"])
def test_a_reading_straying_across_the_floor_mints_one_want_and_withdraws_none_until_it_clears(
        tmp_path, monkeypatch, caplog, narrower):
    """A grower holding no pump, so nothing repairs the bed, and the probe read across its floor of
    0.30 by a ten-thousandth either way — the simulator's count — a reading a cadence: one want, minted
    at the first reading below and kept through every reading back above the floor, withdrawn as
    reached by the reading clear of the narrower range of 0.3002. The world stating no narrower range
    mints a want at every crossing below and withdraws it at every crossing back, three of each."""
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    caplog.set_level(logging.INFO)
    runtime, _ = _grower(_world(tmp_path, narrower=narrower, pump=False))
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    for n, value in enumerate(STRAYING):
        time["at"] = NOW + timedelta(minutes=10 * n)
        runtime.deliver(SOIL, json.dumps({"value": value}).encode(), time["at"])
        runtime.deliver("sensors/thermometer/reading", json.dumps({"value": 21.0 + n / 100}).encode(), time["at"])
        runtime.run(passes=1, poll_s=0)
    life = _life(caplog)
    if narrower:
        assert life == [("minted", ""), ("withdrawn", "reached")], life
    else:
        assert life == [("minted", ""), ("withdrawn", "reached")] * 3, life


@pytest.mark.parametrize("narrower", [True, False], ids=["narrower", "none"])
def test_a_dose_that_leaves_the_bed_short_of_the_narrower_range_is_given_again(tmp_path, monkeypatch, narrower):
    """THE DOSE REACHES THE NARROWER RANGE, AND IS HELD TO IT. 0.2998, below the floor: the dose is
    sized to the operating range's middle, 0.45 — inside the narrower range, where the want is reached
    — and its effect says the reading comes to be inside every range it was below, the narrower one
    among them, so the plan's world reads the want met. The next reading says 0.3001: back above the
    floor and short of 0.3002, a dose that did not take. Held to what it predicted, the step is not
    answered by that, its patience runs out and the want, unreached, is dosed again from where the bed
    stands. Stating no narrower range, 0.3001 is inside every range the bed states, the step is
    answered, the want reached, and the bed left a ten-thousandth above its floor."""
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    runtime, broker = _grower(_world(tmp_path, narrower=narrower))
    runtime.deliver("sensors/thermometer/reading", b'{"value": 21.0}', NOW)
    runtime.deliver(SOIL, b'{"value": 0.2998}', NOW)
    runtime.run(passes=1, poll_s=0)
    assert broker.published == [("actuators/pump/command", {"dose_ml": 300})], "(0.45 - 0.2998) by two litres a fraction"
    for minutes, value in ((10, 0.3001), (12, 0.3001)):
        time["at"] = NOW + timedelta(minutes=minutes)
        runtime.deliver("sensors/thermometer/reading", json.dumps({"value": 21.0 + minutes / 100}).encode(), time["at"])
        runtime.deliver(SOIL, json.dumps({"value": value}).encode(), time["at"])
        runtime.run(passes=2, poll_s=0)
    if narrower:
        assert broker.published == [("actuators/pump/command", {"dose_ml": 300})] * 2, broker.published
        time["at"] = NOW + timedelta(minutes=22)
        runtime.deliver(SOIL, b'{"value": 0.45}', time["at"])
        runtime.run(passes=2, poll_s=0)
        assert runtime.parts["execution"].executor.walking() == [], "the second dose answered, inside the narrower range"
        assert len(broker.published) == 2, "and the want reached, so nothing more"
    else:
        assert broker.published == [("actuators/pump/command", {"dose_ml": 300})], broker.published
        assert runtime.parts["execution"].executor.walking() == []


class Bus:
    """One broker for the simulator and the grower: a reading reaches the grower, a command the
    simulator."""

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
            self.commands.append(topic)
            self.simulator.command(topic, payload)


#  A PROBE AS NOISY AS THE TERRACE'S IS COARSE: a count of 1/375 is 0.0027, and this one strays 0.002
#  either way. The narrower range is sized from it as the world's is, by the whole spread: 0.004 inside
#  each bound.
JITTER = 0.002


def _noisy(world: Path, *, dries: float, starts: float) -> None:
    """The copied greenhouse's probe as noisy as `JITTER`, its bed starting at `starts` and drying
    `dries` a day, and its narrower range — where it states one — sized from that noise."""
    text = (world / "world.ttl").read_text()
    for old, new in (("sim:initialValue 0.31 ; sim:minValue 0.0 ; sim:maxValue 1.0 ]",
                      f"sim:initialValue {starts} ; sim:minValue 0.0 ; sim:maxValue 1.0 ; sim:jitter {JITTER} ]"),
                     ("climate:driesPerDay 0.04 ;", f"climate:driesPerDay {dries} ;"),
                     ("schema:minValue 0.3002 ; schema:maxValue 0.5998 ;", "schema:minValue 0.304 ; schema:maxValue 0.596 ;")):
        assert old in text, old
        text = text.replace(old, new)
    (world / "world.ttl").write_text(text)


def _simulated(world: Path, monkeypatch, cadences: int) -> list[float]:
    """The grower and #879's simulator on one bus, a reading and a pass a cadence for `cadences`
    cadences: the soil's readings."""
    from simulation.simulator import Simulator

    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    bus = Bus()
    bus.simulator = Simulator(world, bus, now=NOW)
    bus.runtime = Runtime(boot(world, "grower"), "grower", transport=Mqtt(GH + "grower", bus))
    bus.simulator.open()
    readings = []
    for n in range(cadences):
        time["at"] = NOW + timedelta(minutes=10 * n)
        readings += [v for t, v in bus.simulator.step(time["at"]) if "moisture" in t]
        bus.runtime.run(passes=1, poll_s=0)
    return readings


@pytest.mark.parametrize("narrower", [True, False], ids=["narrower", "none"])
def test_a_bed_resting_at_its_floor_on_the_simulator_mints_one_want_for_the_dip(tmp_path, monkeypatch, caplog, narrower):
    """#879's simulator, its probe's jitter raised to 0.002, the bed at rest at 0.3005 — nothing dries
    it — and the grower holding no pump: five hours of readings a cadence apart, and the noise alone
    says which side of the floor each falls. With the narrower range one want is minted, at the first
    reading below, and none is withdrawn, since no reading of a bed resting a twentieth of a count
    above its floor reaches 0.304. Stating none, the grower minted a want at a reading below and
    withdrew it as reached at the next above — measured on this seed: thirty readings, nine below
    the floor, fourteen crossings, and seven wants minted and withdrawn where the narrower range
    minted one and withdrew none."""
    world = _world(tmp_path, narrower=narrower, pump=False)
    _noisy(world, dries=0.0, starts=0.3005)
    caplog.set_level(logging.INFO)
    readings = _simulated(world, monkeypatch, 30)
    crossings = sum(1 for a, b in zip(readings, readings[1:]) if (a < 0.30) != (b < 0.30))
    below = [v for v in readings if v < 0.30]
    assert below and crossings > 4 and max(readings) < 0.304, (crossings, readings)
    life = _life(caplog)
    if narrower:
        assert life == [("minted", "")], life
    else:
        minted = life.count(("minted", ""))
        assert minted > 2 and life.count(("withdrawn", "reached")) >= minted - 1, (crossings, life)


def test_a_bed_drying_through_its_floor_on_the_simulator_mints_one_want(tmp_path, monkeypatch, caplog):
    """The same noise on a bed drying a hundredth a day from 0.303 — a fortieth of the noise a cadence,
    so for hours around the floor the noise and not the drying decides which side a reading falls —
    over fifteen hours that carry it well below: one want, and none withdrawn. A FORESEEN crossing
    holds it too, since a desire reading unmet at a ground ahead implies the want whatever the present
    reads, so the world stating no narrower range does not chatter here on this seed either; what the
    narrower range adds is that a want is reached only clear of it, whatever the forecast."""
    world = _world(tmp_path, narrower=True, pump=False)
    _noisy(world, dries=0.01, starts=0.303)
    caplog.set_level(logging.INFO)
    readings = _simulated(world, monkeypatch, 90)
    crossings = sum(1 for a, b in zip(readings, readings[1:]) if (a < 0.30) != (b < 0.30))
    assert readings[0] >= 0.30 > readings[-1] and crossings > 2, (crossings, readings)
    assert _life(caplog) == [("minted", "")]
