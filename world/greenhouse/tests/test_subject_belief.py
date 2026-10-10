"""The greenhouse's subject beliefs (#944, knowledge/domain/belief/transition.md): what the grower
holds true of its bed, in climate's words, made by the running agent of every reading — belief's part
revising the observation and then applying the transitions it triggers, climate's soil and air
(`domains/climate/rules.ttl`) — and held by the margins the bed's operating range states, 0.0002 on
the soil and 0.02 on the air (a-transition-changes-the-state-and-an-inference-only-concludes).

Nothing the grower does reads a subject belief yet, so this holds the belief alone: every other
greenhouse figure is the suite's beside it, unchanged.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyoxigraph as ox

from agent import clock
from agent.runtime import Runtime, boot
from agent.store import graphs_of, revisions_of, rows, update
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
CADENCE = timedelta(minutes=10)
GH = "http://example.org/orexis/world/greenhouse#"
CLIMATE = "http://example.org/orexis/climate#"
STATE = "http://example.org/orexis#StateGraph"
SOIL, AIR = "sensors/moisture_probe/reading", "sensors/thermometer/reading"

#  THE GROWER'S OWN STATE: every state graph it derived, which is where a transition writes and where
#  sensing says a sensor silent or stuck — never an observation, which is a state graph it received.
_DERIVED_Q = """SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?g a orexis:StateGraph ; orexis:arrivedBy orexis:Derived } }"""

#  WHAT THE BED IS BELIEVED, in climate's words, for one property: its state.
_BELIEVED_Q = """SELECT ?state WHERE { $bed $state_as ?state }"""

#  A GRAPH'S PERIOD, owner and arrival, off its row.
_ROW_Q = """SELECT ?start ?end ?owner ?arrival WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    $g dcterms:temporal ?p ; orexis:beliefsOf ?owner ; orexis:arrivedBy ?arrival . ?p orexis:start ?start ; orexis:end ?end } }"""


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


def _own_state(beliefs, at: datetime | None = None) -> list[str]:
    """The grower's own state graphs — holding at `at` where given."""
    derived = {r["g"] for r in rows(beliefs, _DERIVED_Q)}
    return [g for g in (graphs_of(beliefs, STATE, at=at) if at is not None else graphs_of(beliefs, STATE)) if g in derived]


def _believed(beliefs, words: str, at: datetime | None = None) -> str | None:
    """The bed's state in climate's `words`, in the grower's own state — holding at `at` where given."""
    found = rows(beliefs, _BELIEVED_Q, _own_state(beliefs, at), bed=GH + "bed", state_as=CLIMATE + words)
    assert len(found) <= 1, f"one state of the bed's {words} at a time, and {len(found)} stand: {found}"
    return found[0]["state"].rsplit("#", 1)[-1] if found else None


def _read(runtime, time, topic: str, values) -> list:
    """Each of `values` read on `topic` a cadence apart, a pass after each: what the bed was believed."""
    out = []
    for value in values:
        runtime.deliver(topic, json.dumps({"value": value}).encode(), time["at"])
        runtime.run(passes=1, poll_s=0)
        out.append(_believed(runtime.beliefs, "soil" if topic == SOIL else "air"))
        time["at"] += CADENCE
    return out


def test_the_bed_believed_dry_stays_dry_until_its_soil_clears_the_floor_and_the_margin(monkeypatch):
    """0.2990, then 0.3001 three times, then 0.3002, against the floor of 0.30 and the soil's margin of
    0.0002: dry four times, moist at the fifth; and from moist, 0.2999 is dry at once — a value coming
    from another state crosses at the bound itself."""
    runtime, time = _grower(monkeypatch)
    believed = _read(runtime, time, SOIL, [0.2990, 0.3001, 0.3001, 0.3001, 0.3002, 0.2999])
    assert believed == ["Dry"] * 4 + ["Moist", "Dry"], believed


def test_the_bed_believed_wet_stays_wet_until_its_soil_falls_to_the_ceiling_less_the_margin(monkeypatch):
    """The soil's other end, since climate writes the hold once per property and once per bound: 0.6010
    is wet, 0.5999 and 0.5999 still wet against the ceiling of 0.60 less 0.0002, and 0.5998 moist."""
    runtime, time = _grower(monkeypatch)
    believed = _read(runtime, time, SOIL, [0.6010, 0.5999, 0.5999, 0.5998])
    assert believed == ["Wet", "Wet", "Wet", "Moist"], believed


def test_the_first_reading_has_no_state_before_it_and_is_judged_at_the_bare_bound(monkeypatch):
    """0.3001 with nothing held of the bed's soil is moist: the margin holds a state, and there is none
    to hold. The same number after a dry reading is dry."""
    runtime, time = _grower(monkeypatch)
    assert _read(runtime, time, SOIL, [0.3001, 0.2990, 0.3001]) == ["Moist", "Dry", "Dry"]


def test_with_no_margin_the_state_follows_the_bare_bound(monkeypatch):
    """The bed's ranges stating no margin: 0.2990 is dry and 0.3001 moist at once, as the bounds alone
    say, since the transition coalesces an absent margin to nought."""
    runtime, time = _grower(monkeypatch)
    update(runtime.beliefs, "DELETE WHERE { GRAPH ?g { ?condition sensing:margin ?margin } }")
    assert not rows(runtime.beliefs, "SELECT ?m WHERE { GRAPH ?g { ?c sensing:margin ?m } }"), "the margins are gone"
    assert _read(runtime, time, SOIL, [0.2990, 0.3001]) == ["Dry", "Moist"]


def test_the_bed_believed_cold_stays_cold_until_its_air_clears_the_floor_and_the_margin(monkeypatch):
    """17.99, 18.01, then 18.02 against the air's floor of 18 and its margin of 0.02: cold, cold,
    comfortable; then hot past 24 and still at 23.99, comfortable at 23.98; and cold again at once at
    17.99. The air's own transition, by the air's own range and margin."""
    runtime, time = _grower(monkeypatch)
    believed = _read(runtime, time, AIR, [17.99, 18.01, 18.02, 24.01, 23.99, 23.98, 17.99])
    assert believed == ["Cold", "Cold", "Comfortable", "Hot", "Hot", "Comfortable", "Cold"], believed


def test_the_subject_belief_says_the_state_and_no_number(monkeypatch):
    """The bed's soil is one triple, its state: the number stays the observation's, where prediction
    and a command sizing its step read it, and nothing about the bed in the subject belief is a literal."""
    runtime, time = _grower(monkeypatch)
    _read(runtime, time, SOIL, [0.3104])
    (believed,) = _own_state(runtime.beliefs)
    said = [(q.subject.value, q.predicate.value, q.object) for q in runtime.beliefs.quads_for_pattern(None, None, None, ox.NamedNode(believed))]
    assert said == [(GH + "bed", CLIMATE + "soil", ox.NamedNode(CLIMATE + "Moist"))], said
    (observed,) = graphs_of(runtime.beliefs, "http://example.org/orexis/sensing#ObservationGraph")
    readings = [q.object.value for g in [observed, *revisions_of(runtime.beliefs, observed)]
                for q in runtime.beliefs.quads_for_pattern(None, ox.NamedNode("http://www.w3.org/ns/sosa/hasSimpleResult"), None, ox.NamedNode(g))]
    assert readings == ["0.3104"], "the number is where it was"


def test_a_subject_belief_ends_with_the_observation_it_was_made_of(monkeypatch):
    """The probe reports every ten minutes, so its observation holds until twenty past, the next due and
    a grace past it; the subject belief holds over that period too, the grower's own and derived, and a
    reader standing past it — a silence — is handed none."""
    runtime, time = _grower(monkeypatch)
    _read(runtime, time, SOIL, [0.25])
    (believed,) = _own_state(runtime.beliefs)
    (observed,) = graphs_of(runtime.beliefs, "http://example.org/orexis/sensing#ObservationGraph")
    when = lambda row: (datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"]))
    (held,) = rows(runtime.beliefs, _ROW_Q, (), g=believed)
    (seen,) = rows(runtime.beliefs, _ROW_Q, (), g=observed)
    assert when(held) == when(seen) == (NOW, NOW + 2 * CADENCE)
    assert (held["owner"], held["arrival"]) == (GH + "grower", "http://example.org/orexis#Derived")
    assert _believed(runtime.beliefs, "soil", at=NOW + 2 * CADENCE - timedelta(seconds=1)) == "Dry"
    assert _believed(runtime.beliefs, "soil", at=NOW + 2 * CADENCE) is None, "past its period, as past the observation's"


def test_the_readings_one_message_carries_are_taken_in_turn(monkeypatch):
    """A message carrying 0.2990 taken 25 seconds before and 0.3001 now: the earlier is dry at the bare
    bound, and the latest is judged beside that state, so it is dry too — judged with nothing before it,
    0.3001 would have been moist. The earlier's state is taken out where it stood, and the latest's
    stands in the latest's own graph."""
    runtime, time = _grower(monkeypatch)
    runtime.deliver(SOIL, json.dumps({"value": [{"value": 0.2990, "age_s": 25}, {"value": 0.3001, "age_s": 0}]}).encode(), NOW)
    runtime.run(passes=1, poll_s=0)
    (believed,) = _own_state(runtime.beliefs)
    assert _believed(runtime.beliefs, "soil") == "Dry"
    assert "earlier" not in believed, believed


def test_a_revision_a_budget_cut_short_is_believed_as_it_would_have_been(monkeypatch):
    """Ten rule executions a pass: a reading's first pass concludes what it is of and its quantity and
    is cut short before its reading and the transitions; the passes after finish it. Nothing is
    believed of the bed until then, and once finished the state is the one an uncut pass reaches —
    dry, then held dry at 0.3001."""
    runtime, time = _grower(monkeypatch)
    deliberator = runtime.parts["belief"].deliberator
    deliberator.budget = 10
    observed = lambda: set(graphs_of(runtime.beliefs, "http://example.org/orexis/sensing#ObservationGraph"))
    #  WHETHER THE READING WAS LEFT UNDONE, after each pass of the deliberator's — a runtime pass runs
    #  several, one for every graph written, predictions among them.
    left: list[bool] = []
    deliberate = deliberator.deliberate
    deliberator.deliberate = lambda now=None: (spent := deliberate(now), left.append(bool(observed() & set(deliberator.pending))))[0]

    def finished(value) -> None:
        """Passes until the reading is done with — revised and transitioned on — however many it takes;
        the predictions written in between are the deliberator's too, and not waited for. The part runs
        the deliberator's pass where a graph is written, so a reading cut short with nothing written
        after it waits for the next; this calls the pass as that next write would."""
        left.clear()
        runtime.deliver(SOIL, json.dumps({"value": value}).encode(), time["at"])
        runtime.run(passes=1, poll_s=0)
        for _ in range(50):
            if not observed() & set(deliberator.pending):
                assert True in left, "the budget never cut the reading short, and this measures nothing"
                return
            deliberator.deliberate(time["at"])
        raise AssertionError("the reading was never done with")

    finished(0.2990)
    assert _believed(runtime.beliefs, "soil") == "Dry"
    time["at"] += CADENCE
    finished(0.3001)
    assert _believed(runtime.beliefs, "soil") == "Dry", "held, as an uncut pass holds it"


def test_a_subject_belief_is_kept_in_a_volume_lived_in(monkeypatch):
    """The subject belief is the grower's own: booted again on the same store, the bed is still believed
    dry, and the next reading in the margin is judged beside it — dry, not moist as a first reading
    would be."""
    runtime, time = _grower(monkeypatch)
    _read(runtime, time, SOIL, [0.2990])
    again, later = _grower(monkeypatch, runtime.beliefs)
    assert _believed(again.beliefs, "soil") == "Dry"
    later["at"] = NOW + CADENCE
    assert _read(again, later, SOIL, [0.3001]) == ["Dry"]
