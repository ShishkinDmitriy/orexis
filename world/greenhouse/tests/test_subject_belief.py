"""The greenhouse's subject beliefs (#944, knowledge/domain/sensing/subject-belief.md): what the grower
holds true of its bed, in climate's words, made by the running agent of every reading — belief's part
revising it beside what the world states and the subject belief before, sensing's part writing what
the rule judged — and held by the margins the bed's operating range states, 0.0002 on the soil and
0.02 on the air.

Nothing the grower does reads a subject belief yet, so this holds the belief alone: every other
greenhouse figure is the suite's beside it, unchanged.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.runtime import Runtime, boot
from agent.store import graphs_of, rows
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
GH = "http://example.org/orexis/world/greenhouse#"
SUBJECT_BELIEF = "http://example.org/orexis/sensing#SubjectBeliefGraph"
SOIL, AIR = "sensors/moisture_probe/reading", "sensors/thermometer/reading"

#  WHAT THE BED IS BELIEVED, in climate's words, for one property: its state and its value.
_BELIEVED_Q = """PREFIX climate: <http://example.org/orexis/climate#>
SELECT ?state ?value WHERE { $bed $state_as ?state ; $value_as ?value }"""


class _Broker:
    def subscribe(self, pattern):
        pass

    def publish(self, topic, payload, retain=False):
        pass


def _grower(monkeypatch, store=None):
    time = {"at": NOW}
    monkeypatch.setattr(clock, "now", lambda: time["at"])
    beliefs = boot(WORLD, "grower", store)
    return Runtime(beliefs, "grower", transport=Mqtt(GH + "grower", _Broker())), time


def _believed(beliefs, words: str) -> tuple[str, float] | None:
    state_as, value_as = {"soil": ("soil", "moisture"), "air": ("air", "temperature")}[words]
    climate = "http://example.org/orexis/climate#"
    found = rows(beliefs, _BELIEVED_Q, graphs_of(beliefs, SUBJECT_BELIEF), bed=GH + "bed",
                 state_as=climate + state_as, value_as=climate + value_as)
    assert len(found) <= 1, found
    return (found[0]["state"].rsplit("#", 1)[-1], round(float(found[0]["value"]), 6)) if found else None


def _read(runtime, time, topic: str, values) -> list:
    """Each of `values` read on `topic` a cadence apart, a pass after each: what the bed was believed."""
    out = []
    for value in values:
        runtime.deliver(topic, json.dumps({"value": value}).encode(), time["at"])
        runtime.run(passes=1, poll_s=0)
        out.append(_believed(runtime.beliefs, "soil" if topic == SOIL else "air"))
        time["at"] += timedelta(minutes=10)
    return out


def test_the_bed_believed_dry_stays_dry_until_its_soil_clears_the_floor_and_the_margin(monkeypatch):
    """0.2990, then 0.3001 three times, then 0.3002, against the floor of 0.30 and the soil's margin of
    0.0002: dry four times, moist at the fifth; and from moist, 0.2999 is dry at once."""
    runtime, time = _grower(monkeypatch)
    believed = _read(runtime, time, SOIL, [0.2990, 0.3001, 0.3001, 0.3001, 0.3002, 0.2999])
    assert [b[0] for b in believed] == ["Dry"] * 4 + ["Moist", "Dry"], believed
    assert [b[1] for b in believed] == [0.299, 0.3001, 0.3001, 0.3001, 0.3002, 0.2999], "the value is the reading"


def test_the_bed_believed_cold_stays_cold_until_its_air_clears_the_floor_and_the_margin(monkeypatch):
    """17.99, 18.01, then 18.02 against the air's floor of 18 and its margin of 0.02: cold, cold,
    comfortable; and 24.5 is hot."""
    runtime, time = _grower(monkeypatch)
    believed = _read(runtime, time, AIR, [17.99, 18.01, 18.02, 24.5])
    assert [b[0] for b in believed] == ["Cold", "Cold", "Comfortable", "Hot"], believed


def test_a_subject_belief_is_kept_in_a_volume_lived_in(monkeypatch):
    """The subject belief is the grower's own: booted again on the same store, the bed is still believed
    dry, and the next reading in the margin is judged beside it — dry, not moist as a first reading
    would be."""
    runtime, time = _grower(monkeypatch)
    _read(runtime, time, SOIL, [0.2990])
    again, later = _grower(monkeypatch, runtime.beliefs)
    assert _believed(again.beliefs, "soil") == ("Dry", 0.299)
    later["at"] = NOW + timedelta(minutes=10)
    assert _read(again, later, SOIL, [0.3001]) == [("Dry", 0.3001)]
