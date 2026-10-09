"""The greenhouse's hysteresis (#944): a reading judged below the bed's comfortable floor stays below
until it clears the floor and its margin (`orexis:margin`, knowledge/domain/kernel/margin.md), so a
reading the probe's noise carries back and forth across the floor mints one want, and the want is
withdrawn once the value has cleared it.

Each case runs the grower twice where the contrast is the point: on the world as it is, and on the
world stating no margin, where a side is the bare comparison of one reading with the bounds — the
guard: the same readings there mint a want per crossing and withdraw it per crossing back. The bed is
at REST in the straying cases, since a drying bed's want is held by foresight whether a margin is
stated or not: a want minted for a foreseen crossing is weighed at its instant, and a desire reading
unmet at a ground ahead keeps it whatever the present reads. The chatter is a bed at rest at its
floor, or a want rooted in the present — which is what is held here.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.runtime import Runtime, boot
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"
SOIL = "sensors/moisture_probe/reading"
AIR = "sensors/thermometer/reading"

#  THE MARGINS THE BED STATES, as the world spells them.
MARGINS = ("orexis:margin 0.0002 ;", "orexis:margin 0.02 ;")


class Broker:
    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, json.loads(payload)))


def _world(tmp_path: Path, *, margin: bool = True, pump: bool = True, dries: float | None = None) -> Path:
    """The greenhouse, copied — as it is, or stating no margin; with a grower that holds no pump, so a
    dry bed stands unrepaired; and with the bed drying `dries` a day where that is given."""
    world = tmp_path / "world" / "greenhouse"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / "domains").symlink_to(WORLD.parents[1] / "domains")
    text = (world / "world.ttl").read_text()
    if not margin:
        for said in MARGINS:
            assert said in text, said
            text = text.replace(said, "")
    if dries is not None:
        assert "climate:driesPerDay 0.04 ;" in text
        text = text.replace("climate:driesPerDay 0.04 ;", f"climate:driesPerDay {dries} ;")
    (world / "world.ttl").write_text(text)
    if not pump:
        society = (world / "society.ttl").read_text()
        assert "actuation:hasActuator :pump , :heater ." in society
        (world / "society.ttl").write_text(society.replace("actuation:hasActuator :pump , :heater .",
                                                           "actuation:hasActuator :heater ."))
    return world


def _grower(world: Path):
    broker = Broker()
    return Runtime(boot(world, "grower"), "grower", transport=Mqtt(GH + "grower", broker)), broker


def _life(caplog) -> list[str]:
    """What happened to the soil's want, in order: minted, or withdrawn — once per withdrawal, which is
    said twice, by the derivation that no longer reads it unmet and by the pass that weighs it met in
    the present ground, one act."""
    out = []
    for r in caplog.records:
        said = r.getMessage()
        if r.name == "derive_wants" and "pursuing" in said and "SoilMoisture" in said:
            out.append("minted")
        if r.name == "withdraw" and re.match(r".*SoilMoisture withdrawn: ", said) and out[-1:] != ["withdrawn"]:
            out.append("withdrawn")
    return out


#  ACROSS THE FLOOR OF 0.30 BY A TEN-THOUSANDTH EACH WAY — the simulator's count — AND THEN CLEAR OF
#  THE FLOOR AND ITS MARGIN, 0.3002.
STRAYING = [0.3001, 0.2999, 0.3001, 0.2999, 0.3001, 0.2999, 0.3003]


@pytest.mark.parametrize("margin", [True, False], ids=["margin", "none"])
def test_a_reading_straying_across_the_floor_mints_one_want_and_withdraws_it_once_cleared(
        tmp_path, monkeypatch, caplog, margin):
    """No pump, the bed at rest, and the probe read across its floor by a ten-thousandth either way, a
    reading a cadence: one want, minted at the first reading below and kept through every reading
    back over the floor and short of 0.3002 — the side held below by the margin — and withdrawn by the
    reading clear of it. The world stating no margin mints a want at every crossing below and
    withdraws it at every crossing back, three of each."""
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    caplog.set_level(logging.INFO)
    runtime, _ = _grower(_world(tmp_path, margin=margin, pump=False, dries=0.0))
    for n, value in enumerate(STRAYING):
        time["at"] = NOW + timedelta(minutes=10 * n)
        runtime.deliver(SOIL, json.dumps({"value": value}).encode(), time["at"])
        runtime.deliver(AIR, json.dumps({"value": 21.0 + n / 100}).encode(), time["at"])
        runtime.run(passes=1, poll_s=0)
    life = _life(caplog)
    assert life == (["minted", "withdrawn"] if margin else ["minted", "withdrawn"] * 3), life


def test_a_dose_aimed_at_the_middle_lands_inside_though_the_reading_before_was_below(tmp_path, monkeypatch):
    """THE DOSE STILL LANDS. 0.2998, below the floor: the dose is sized to the range's middle, 0.45 — its
    effect says the reading comes to be inside the range, in the possible world the search stands in,
    where no rule runs — and the next reading, carrying the side the one before was judged on, reads
    0.45: past the floor and its margin, inside, so the step is answered and the want reached."""
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    runtime, broker = _grower(_world(tmp_path))
    runtime.deliver(AIR, b'{"value": 21.0}', NOW)
    runtime.deliver(SOIL, b'{"value": 0.2998}', NOW)
    runtime.run(passes=1, poll_s=0)
    assert broker.published == [("actuators/pump/command", {"dose_ml": 300})], "(0.45 - 0.2998) by two litres a fraction"
    time["at"] = NOW + timedelta(minutes=10)
    runtime.deliver(AIR, b'{"value": 21.1}', time["at"])
    runtime.deliver(SOIL, b'{"value": 0.45}', time["at"])
    runtime.run(passes=2, poll_s=0)
    assert runtime.parts["execution"].executor.walking() == [], "the dose answered, inside"
    assert len(broker.published) == 1, "and the want reached, so nothing more"


@pytest.mark.parametrize("margin", [True, False], ids=["margin", "none"])
def test_a_dose_that_leaves_the_bed_within_the_margin_is_given_again(tmp_path, monkeypatch, margin):
    """AND IS HELD TO THE MARGIN. 0.2998 is dosed; the next readings say 0.3001 — over the floor and
    short of the floor and its margin, a dose that did not take. The reading before was below, so the
    side is still below, the step is not answered, its patience runs out and the want, still standing,
    is dosed again from where the bed stands. Stating no margin, 0.3001 is inside, the step is
    answered, the want reached, and the bed left a ten-thousandth above its floor."""
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    runtime, broker = _grower(_world(tmp_path, margin=margin))
    runtime.deliver(AIR, b'{"value": 21.0}', NOW)
    runtime.deliver(SOIL, b'{"value": 0.2998}', NOW)
    runtime.run(passes=1, poll_s=0)
    assert broker.published == [("actuators/pump/command", {"dose_ml": 300})]
    for minutes in (10, 12):
        time["at"] = NOW + timedelta(minutes=minutes)
        runtime.deliver(AIR, json.dumps({"value": 21.0 + minutes / 100}).encode(), time["at"])
        runtime.deliver(SOIL, b'{"value": 0.3001}', time["at"])
        runtime.run(passes=2, poll_s=0)
    if margin:
        assert broker.published == [("actuators/pump/command", {"dose_ml": 300})] * 2, broker.published
    else:
        assert broker.published == [("actuators/pump/command", {"dose_ml": 300})], broker.published
        assert runtime.parts["execution"].executor.walking() == []


class Bus:
    """One broker for the simulator and the grower: a reading reaches the grower, a command the
    simulator."""

    def __init__(self):
        self.runtime = self.simulator = None

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        if topic.startswith("sensors/"):
            self.runtime.deliver(topic, payload, clock.now())
        else:
            self.simulator.command(topic, payload)


#  A PROBE AS NOISY AS THE TERRACE'S IS COARSE: a count of 1/375 is 0.0027, and this one strays 0.002
#  either way. The margin is sized from it as the world's is, by the whole spread: 0.004.
JITTER = 0.002


def _noisy(world: Path, *, dries: float, starts: float, margin: bool) -> None:
    """The copied greenhouse's probe as noisy as `JITTER`, its bed starting at `starts` and drying
    `dries` a day, and its soil's margin — where it states one — sized from that noise."""
    text = (world / "world.ttl").read_text()
    edits = [("sim:initialValue 0.31 ; sim:minValue 0.0 ; sim:maxValue 1.0 ]",
              f"sim:initialValue {starts} ; sim:minValue 0.0 ; sim:maxValue 1.0 ; sim:jitter {JITTER} ]"),
             ("climate:driesPerDay 0.04 ;", f"climate:driesPerDay {dries} ;")]
    if margin:
        edits.append(("orexis:margin 0.0002 ;", f"orexis:margin {2 * JITTER} ;"))
    for old, new in edits:
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


@pytest.mark.parametrize("margin", [True, False], ids=["margin", "none"])
def test_a_bed_resting_at_its_floor_on_the_simulator_mints_one_want_for_the_dip(tmp_path, monkeypatch, caplog, margin):
    """#879's simulator, its probe's jitter raised to 0.002, the bed at rest at 0.3005 — nothing dries
    it — and the grower holding no pump: five hours of readings a cadence apart, and the noise alone
    says which side of the floor each falls. With the margin one want is minted, at the first reading
    below, and none is withdrawn, since no reading of a bed resting a twentieth of a count above its
    floor reaches 0.304. Stating none, the grower minted a want at a reading below and withdrew it at
    the next above — measured on seed 0: thirty readings, nine below the floor, fourteen crossings,
    seven wants minted and seven withdrawn, where the margin minted one and withdrew none."""
    world = _world(tmp_path, margin=margin, pump=False)
    _noisy(world, dries=0.0, starts=0.3005, margin=margin)
    caplog.set_level(logging.INFO)
    readings = _simulated(world, monkeypatch, 30)
    crossings = sum(1 for a, b in zip(readings, readings[1:]) if (a < 0.30) != (b < 0.30))
    below = [v for v in readings if v < 0.30]
    assert (len(readings), len(below), crossings) == (30, 9, 14) and max(readings) < 0.304, (crossings, readings)
    life = _life(caplog)
    assert life == (["minted"] if margin else ["minted", "withdrawn"] * 7), life


def test_a_bed_drying_through_its_floor_on_the_simulator_is_one_want_with_no_margin(tmp_path, monkeypatch, caplog):
    """WHAT THE MARGIN IS NOT FOR. The same noise on a bed drying a hundredth a day from 0.303 — a
    fortieth of the noise a cadence, so for hours around the floor the noise and not the drying decides
    which side a reading falls — over fifteen hours that carry it well below, on the world stating NO
    margin: one want, and none withdrawn, though the readings cross the floor nineteen times on seed 0.
    A FORESEEN crossing holds it: a want minted for a foreseen crossing is weighed at its instant, and
    the desire, reading unmet at a ground ahead, keeps it whatever the present reads. So the chatter a
    margin stops is a bed at rest at its floor, or a want rooted in the present — the cases above."""
    world = _world(tmp_path, margin=False, pump=False)
    _noisy(world, dries=0.01, starts=0.303, margin=False)
    caplog.set_level(logging.INFO)
    readings = _simulated(world, monkeypatch, 90)
    crossings = sum(1 for a, b in zip(readings, readings[1:]) if (a < 0.30) != (b < 0.30))
    assert readings[0] >= 0.30 > readings[-1] and crossings == 19, (crossings, readings)
    assert _life(caplog) == ["minted"]
