"""The number a simulated sensor publishes is the instrument's and not the model's (#879).

The simulator is held to its one promise to sensing here: a sensor nothing touches — the thermometer
of a greenhouse nobody heats, a probe clamped at its bound — still publishes a number that moves, by
the model's `sim:jitter` or by a count of what the simulator publishes to where the model states
none, and never the same number twice running; and the noise is reproducible under the seed and
touches the model's reading not at all. The greenhouse is the world read, since it states a jitter on
one instrument and none on the other.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.sensing.received import STUCK_AFTER
from simulation.simulator import JITTER, PLACES, Simulator

WORLD = Path(__file__).resolve().parents[2] / "world" / "greenhouse"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
CADENCE = timedelta(minutes=10)
GH = "http://example.org/orexis/world/greenhouse#"
THERMOMETER, PROBE = GH + "thermometer", GH + "moisture_probe"
HALF_A_COUNT = 10.0 ** -PLACES / 2


class Client:
    """The simulator's broker: every publish, kept."""

    def __init__(self):
        self.published = []

    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload))


def _readings(simulator: Simulator, cadences: int, start: datetime = NOW) -> dict[str, list[tuple[float, float]]]:
    """`cadences` readings of every sensor, one per cadence from `start`: per sensor, the number
    published beside the model's reading at that instant."""
    out: dict[str, list[tuple[float, float]]] = {name: [] for name in simulator.sensors}
    for n in range(cadences):
        published = dict(simulator.step(start + n * CADENCE))
        for name, sensor in simulator.sensors.items():
            out[name].append((published[sensor["topic"]], sensor["value"]))
    return out


def _consecutive_differ(numbers: list[float]) -> bool:
    return all(a != b for a, b in zip(numbers, numbers[1:]))


def test_a_sensor_nothing_touches_publishes_a_number_that_moves():
    """Nobody heats the bed, so the thermometer's model reads 21.0 at every cadence; the number it
    publishes is never the one before through the run sensing would call it stuck over, and strays
    no further than the hundredth of a degree the world states."""
    simulator = Simulator(WORLD, Client(), now=NOW, seed=1)
    readings = _readings(simulator, STUCK_AFTER + 2)
    air = [published for published, _ in readings[THERMOMETER]]
    assert len(air) == STUCK_AFTER + 2 and _consecutive_differ(air), air
    assert all(model == 21.0 for _, model in readings[THERMOMETER]), "the noise is the instrument's: the model never moved"
    assert all(abs(published - 21.0) <= 0.01 + HALF_A_COUNT for published in air), air
    assert max(abs(published - 21.0) for published in air) > JITTER, "the model's jitter was read, not the default"


def test_a_sensor_stating_no_jitter_strays_a_count():
    """The probe's model states none, so its number strays a ten-thousandth either way of the model's
    drying reading — one count of the four places published — and no two in a row are the same."""
    simulator = Simulator(WORLD, Client(), now=NOW, seed=1)
    readings = _readings(simulator, STUCK_AFTER + 2)
    soil = [published for published, _ in readings[PROBE]]
    assert _consecutive_differ(soil), soil
    assert all(abs(published - model) <= JITTER + HALF_A_COUNT for published, model in readings[PROBE]), readings[PROBE]
    #  The drying alone moves the probe three counts a cadence, so differing numbers prove nothing
    #  here: what does is a number that is NOT the model's reading rounded.
    assert any(published != round(model, PLACES) for published, model in readings[PROBE]), "no noise was added"
    assert readings[PROBE][-1][1] < readings[PROBE][0][1] == 0.31, "the bed dried, and the model is the physics alone"


def test_a_sensor_clamped_at_its_bound_still_moves():
    """A probe in a bed dried to its model's floor reads 0.0 at every cadence, clamped there by the
    drying; what it publishes still moves about the bound, since the bound is the model's and the
    noise the instrument's. (The ceiling would not do: a bed soaked to it leaves it by three counts a
    cadence, which is the drying and not the instrument.)"""
    simulator = Simulator(WORLD, Client(), now=NOW, seed=2)
    simulator.sensors[PROBE]["value"] = 0.0
    readings = _readings(simulator, STUCK_AFTER + 2)
    assert all(model == 0.0 for _, model in readings[PROBE]), "the drying holds the model at its floor"
    soil = [published for published, _ in readings[PROBE]]
    assert _consecutive_differ(soil), soil
    assert all(abs(published) <= JITTER + HALF_A_COUNT for published in soil), soil
    assert all(str(published) != "-0.0" for published in soil), "a count below nought is published as a number, not a sign"


def test_the_noise_is_reproducible_under_a_seed_and_the_physics_under_any():
    """Two simulators seeded alike publish the same numbers; seeded apart they publish different
    numbers of the same model readings."""
    alike = [_readings(Simulator(WORLD, Client(), now=NOW, seed=7), STUCK_AFTER) for _ in range(2)]
    assert alike[0] == alike[1]
    apart = _readings(Simulator(WORLD, Client(), now=NOW, seed=8), STUCK_AFTER)
    for sensor in (THERMOMETER, PROBE):
        assert [p for p, _ in apart[sensor]] != [p for p, _ in alike[0][sensor]], sensor
        assert [m for _, m in apart[sensor]] == [m for _, m in alike[0][sensor]], "the model is the physics, whatever the seed"


def test_a_jitter_of_nought_publishes_the_model_exactly():
    """The exception that proves the rule: a model stating nought has nothing to redraw with, so the
    number goes out as the model reads it, and is the stuck instrument #879 found."""
    simulator = Simulator(WORLD, Client(), now=NOW, seed=1)
    simulator.sensors[THERMOMETER]["jitter"] = 0.0
    air = [published for published, _ in _readings(simulator, STUCK_AFTER + 2)[THERMOMETER]]
    assert air == [21.0] * (STUCK_AFTER + 2)
