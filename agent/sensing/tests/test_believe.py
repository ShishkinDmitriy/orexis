"""`believe`, held two ways (knowledge/domain/sensing/subject-belief.md, #944).

Its cases (`believe/`) hold the writer to the store it leaves: given an observation whose revision
says the state its subject was judged in, the subject belief written in the words the property's
domain names, over the observation's period, the one before it replaced whole — and one made of a
later reading left standing.

And the judgment it writes, held through the two parts that make it, as a runtime assembles them:
belief's, revising each graph written beside what the world states and every state graph the agent
derived, and sensing's, linked to it, believing what its deliberator says it revised. A test here may
import the belief package; sensing's code may not.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.belief.create import create as belief_part
from agent.belief.revise import revise
from agent.ontology import BELIEF, PREDICTION, PUBLIC
from agent.sensing.believe import believe
from agent.sensing.create import create as sensing_part
from agent.sensing.ontology import SUBJECT_BELIEF_GRAPH
from agent.sensing.received import received
from agent.store import document, entry, graphs_of, put_document, quads, revisions_of, rows, update

CASES_DIR = Path(__file__).parent / "believe"
CASES = sorted(p for p in CASES_DIR.glob("*.trig") if "." not in p.stem)
WORLD = Path(__file__).parent / "worlds" / "a_bed_and_its_instruments.trig"
SAMPLE = Path(__file__).parent / "worlds" / "a_probe_in_a_sample_of_the_pot.trig"
RULES = Path(__file__).parents[1] / "rules.ttl"
T = "http://example.org/test#"
BELIEVED = "http://example.org/orexis/graph/believed/keeper/"     # the writer's name, for eyes
CADENCE = timedelta(minutes=10)

#  WHICH GRAPH EACH CASE BELIEVES, and the subject beliefs it writes.
BELIEVES = {
    "a_judgment_is_believed_in_the_domains_words": (T + "observed", [BELIEVED + "bed_SoilMoisture"]),
    "a_subject_belief_is_replaced_whole": (T + "observed", [BELIEVED + "bed_SoilMoisture"]),
    "a_subject_belief_of_a_later_reading_stands": (T + "observed_earlier", []),
}

#  WHAT THE BED IS BELIEVED, for one property: its state's local name and its value, in every subject
#  belief graph holding at the instant asked about.
_HELD_Q = """
SELECT ?state ?value WHERE { ?subject ?stateAs ?state ; ?valueAs ?value .
  VALUES (?subject ?stateAs ?valueAs) { ($bed $stateAs $valueAs) } }"""

WORDS = {"SoilMoisture": ("soil", "moisture"), "AirTemperature": ("air", "temperature")}


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_believe_leaves_the_subject_belief_the_patch_says(case, monkeypatch, request, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(case)
    graph, expected = BELIEVES[case.stem]
    assert believe(store, snapshots.ME, graph) == expected
    snapshots.held_to_diff(case, request, "believe", snapshots.snapshot_of(store))


def test_every_case_is_read_and_no_diff_is_orphaned(snapshots):
    assert set(BELIEVES) == {c.stem for c in CASES}, [c.name for c in CASES]
    assert not snapshots.orphans_in(CASES_DIR)


class _Agent:
    """The two parts a subject belief is made by, created, linked and started as a runtime does it: the
    reading `received` writes is handed to belief's part as the runtime hands it a graph written."""

    def __init__(self, store, snapshots, stand_in_runtime, budget: int | None = None):
        put_document(store, document(RULES))
        self.store, self.me = store, snapshots.ME
        self.runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW)
        parts = {"belief": belief_part(self.runtime), "sensing": sensing_part(self.runtime)}
        self.deliberator = parts["belief"].deliberator
        if budget is not None:
            self.deliberator.budget = budget
        for part in parts.values():
            if callable(getattr(part, "link", None)):
                part.link(parts)
        for part in parts.values():
            part.start(self.runtime)
        (self.written,) = [handler for kind, handler in self.runtime.heard if kind == BELIEF]

    def reads(self, sensor: str, value, at: datetime) -> list[str]:
        """`value` read by `sensor` at `at`, every graph written heard as the runtime would have it heard."""
        self.runtime.now = at
        graphs = received(self.store, self.me, T + sensor, json.dumps({"value": value}).encode(), at)
        for graph in graphs:
            self.written(graph)
        return graphs

    def believes(self, observed_property: str = "SoilMoisture", at: datetime | None = None):
        """What the bed is believed of `observed_property`, as (state, value) — at `at` where given,
        else of every subject belief graph whatever its period — or None."""
        state, value = WORDS[observed_property]
        graphs = graphs_of(self.store, SUBJECT_BELIEF_GRAPH, at=at) if at is not None else graphs_of(self.store, SUBJECT_BELIEF_GRAPH)
        found = rows(self.store, _HELD_Q, graphs, bed=T + "bed", stateAs=T + state, valueAs=T + value)
        assert len(found) <= 1, f"one subject belief per key, and {len(found)} stand: {found}"
        return (found[0]["state"].rsplit("#", 1)[-1], float(found[0]["value"])) if found else None


def _sides(store, graph: str) -> set[str]:
    """The sides of the bed's operating range the observation in `graph` was concluded on."""
    return {r["side"].rsplit("#", 1)[-1] for r in rows(store, f"""
        SELECT ?side WHERE {{ ?o ?side <{T}bed.operating> VALUES ?side {{ sensing:below sensing:inside sensing:above }} }}""",
        [graph, *revisions_of(store, graph)])}


@pytest.fixture
def bed(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    return _Agent(snapshots.stand_in(WORLD), snapshots, stand_in_runtime)


def test_a_bed_believed_dry_stays_dry_until_its_reading_clears_the_floor_and_the_margin(bed, snapshots):
    """0.2990, then 0.3001 three times, then 0.3002, a cadence apart, against a floor of 0.30 and a margin
    of 0.0002: dry four times and then moist. The side of each reading is the bare comparison and
    remembers nothing — below once and inside after — while the subject belief holds the state."""
    states, sides = [], []
    for n, value in enumerate([0.2990, 0.3001, 0.3001, 0.3001, 0.3002]):
        (graph,) = bed.reads("probe", value, snapshots.NOW + n * CADENCE)
        states.append(bed.believes())
        sides.append(_sides(bed.store, graph))
    assert states == [("Dry", 0.299), ("Dry", 0.3001), ("Dry", 0.3001), ("Dry", 0.3001), ("Moist", 0.3002)], states
    assert sides == [{"below"}] + [{"inside"}] * 4, sides


def test_a_drop_out_of_the_range_is_believed_at_the_bound(bed, snapshots):
    """Moist at 0.31, then 0.2999: a value coming from another state crosses at the bound itself, so a
    real drop is believed at once and nothing is noticed late."""
    bed.reads("probe", 0.31, snapshots.NOW)
    assert bed.believes() == ("Moist", 0.31)
    bed.reads("probe", 0.2999, snapshots.NOW + CADENCE)
    assert bed.believes() == ("Dry", 0.2999)


def test_with_no_margin_the_state_follows_the_bare_bound(monkeypatch, snapshots, stand_in_runtime):
    """The same world stating no margin: 0.2990 is dry and 0.3001 moist, as the bounds alone say."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    text = WORLD.read_text()
    assert " sensing:margin 0.0002 ;" in text
    bed = _Agent(snapshots.stand_in(WORLD, text.replace(" sensing:margin 0.0002 ;", "")), snapshots, stand_in_runtime)
    bed.reads("probe", 0.2990, snapshots.NOW)
    assert bed.believes() == ("Dry", 0.299)
    bed.reads("probe", 0.3001, snapshots.NOW + CADENCE)
    assert bed.believes() == ("Moist", 0.3001)


def test_the_first_reading_has_nothing_before_it_and_is_judged_at_the_bare_bound(bed, snapshots):
    """0.3001 with no subject belief before it is moist: the margin holds a state, and there is none to
    hold. The same number after a dry reading is dry."""
    bed.reads("probe", 0.3001, snapshots.NOW)
    assert bed.believes() == ("Moist", 0.3001)
    bed.reads("probe", 0.2990, snapshots.NOW + CADENCE)
    bed.reads("probe", 0.3001, snapshots.NOW + 2 * CADENCE)
    assert bed.believes() == ("Dry", 0.3001)


def test_the_value_believed_is_the_reading(bed, snapshots):
    """The value is the observation's reading, the term as it is."""
    (graph,) = bed.reads("probe", 0.3104, snapshots.NOW)
    (reading,) = [q.object for g in [graph, *revisions_of(bed.store, graph)]
                  for q in bed.store.quads_for_pattern(None, ox.NamedNode("http://www.w3.org/ns/sosa/hasSimpleResult"), None, ox.NamedNode(g))]
    (believed,) = graphs_of(bed.store, SUBJECT_BELIEF_GRAPH)
    (value,) = [q.object for q in bed.store.quads_for_pattern(ox.NamedNode(T + "bed"), ox.NamedNode(T + "moisture"), None, ox.NamedNode(believed))]
    assert value == reading and str(value.value) == "0.3104"


def test_the_air_is_cold_comfortable_or_hot_and_held_by_its_own_margin(bed, snapshots):
    """The air's floor of 18 and ceiling of 24, its margin 0.02: cold at 17.99 and still at 18.01, then
    comfortable at 18.02; hot past 24 and still at 23.99, comfortable at 23.98; and cold again at once
    at 17.99. One rule judged both properties, by each one's own range and margin."""
    states = []
    for n, value in enumerate([17.99, 18.01, 18.02, 24.01, 23.99, 23.98, 17.99]):
        bed.reads("thermometer", value, snapshots.NOW + n * CADENCE)
        states.append(bed.believes("AirTemperature")[0])
    assert states == ["Cold", "Cold", "Comfortable", "Hot", "Hot", "Comfortable", "Cold"], states


def test_a_subject_belief_ends_with_the_observation_it_was_made_of(bed, snapshots):
    """The probe reports every ten minutes, so its observation holds until twenty past, the next due and
    a grace past it; the subject belief holds over that period too, and a reader standing past it — a
    silence — is handed none. It is the keeper's own and derived, so a volume lived in keeps it."""
    (graph,) = bed.reads("probe", 0.25, snapshots.NOW)
    period = """SELECT ?start ?end ?owner ?arrival WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
        $g dcterms:temporal ?p ; orexis:beliefsOf ?owner ; orexis:arrivedBy ?arrival . ?p orexis:start ?start ; orexis:end ?end } }"""
    (believed,) = graphs_of(bed.store, SUBJECT_BELIEF_GRAPH)
    (observed,) = rows(bed.store, period, (), g=graph)
    (held,) = rows(bed.store, period, (), g=believed)
    when = lambda row: (datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"]))
    assert when(held) == when(observed) == (snapshots.NOW, snapshots.NOW + 2 * CADENCE)
    assert (held["owner"], held["arrival"]) == (snapshots.ME, "http://example.org/orexis#Derived")
    assert bed.believes(at=snapshots.NOW + 2 * CADENCE - timedelta(seconds=1)) == ("Dry", 0.25)
    assert bed.believes(at=snapshots.NOW + 2 * CADENCE) is None, "past its period, as past the observation's"


def test_the_readings_one_message_carries_are_believed_in_turn(bed, snapshots):
    """A message carrying 0.2990 taken 25 seconds before and 0.3001 now: the earlier is believed dry at
    the bare bound, and the latest is judged beside that subject belief, so it is dry too — judged from
    the latest alone, with nothing before it, it would have been moist."""
    payload = json.dumps({"value": [{"value": 0.2990, "age_s": 25}, {"value": 0.3001, "age_s": 0}]}).encode()
    bed.runtime.now = snapshots.NOW
    graphs = received(bed.store, bed.me, T + "probe", payload, snapshots.NOW)
    assert len(graphs) == 2
    believed = []
    for graph in graphs:
        bed.written(graph)
        believed.append(bed.believes())
    assert believed == [("Dry", 0.299), ("Dry", 0.3001)], believed


def test_a_revision_a_budget_cut_short_is_believed_as_it_would_have_been(monkeypatch, snapshots, stand_in_runtime):
    """Ten rule executions a pass: a reading's first pass concludes what it is of and its reading and is
    cut short before the layer that judges it, and the next finishes it. The subject belief before stands
    until then, and the judgment is the one an uncut pass makes — dry at 0.3001, held — since the revision
    was continued beside the subject belief it was begun beside."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    bed = _Agent(snapshots.stand_in(WORLD), snapshots, stand_in_runtime, budget=10)

    def finished() -> int:
        passes = 0
        while bed.deliberator.pending:
            passes += 1
            assert passes < 50, "the revision never settled"
            bed.deliberator.deliberate(bed.runtime.now)
        return passes

    bed.reads("probe", 0.2990, snapshots.NOW)
    assert bed.deliberator.pending and bed.believes() is None, "cut short, and nothing believed yet"
    assert finished() > 0 and bed.believes() == ("Dry", 0.299)
    bed.reads("probe", 0.3001, snapshots.NOW + CADENCE)
    assert bed.deliberator.pending and bed.believes() == ("Dry", 0.299), "the subject belief before stands"
    assert finished() > 0 and bed.believes() == ("Dry", 0.3001), "held, as an uncut pass holds it"


def test_a_prediction_carrying_a_judgment_forward_is_believed_of_nothing(bed, snapshots):
    """A key no drift moves is carried forward as the observation in hand, judgment and all: a graph of
    that kind is no observation, and nothing is believed of it."""
    (graph,) = bed.reads("probe", 0.25, snapshots.NOW)
    carried = T + "carried"
    bed.store.extend(ox.Quad(q.subject, q.predicate, q.object, ox.NamedNode(carried))
                     for g in [graph, *revisions_of(bed.store, graph)] for q in quads(bed.store, g))
    update(bed.store, f"INSERT DATA {{ {entry(bed.store, carried, PREDICTION, 'http://example.org/orexis#Recorded', snapshots.ME, snapshots.NOW + 2 * CADENCE, snapshots.NOW + 8 * CADENCE)} }}")
    assert rows(bed.store, "SELECT ?s WHERE { ?o sensing:judged ?s }", [carried]), "the judgment is carried"
    assert believe(bed.store, snapshots.ME, carried) == []


def test_a_property_its_domain_names_no_words_for_is_believed_in_none(bed, snapshots):
    """The hygrometer's humidity says no words: its reading is an observation with its sides, and no
    subject belief. And the soil under both its floors is one subject belief, dry by the operating
    range: a survival range is judged into none."""
    bed.reads("hygrometer", 0.5, snapshots.NOW)
    assert graphs_of(bed.store, SUBJECT_BELIEF_GRAPH) == []
    bed.reads("probe", 0.05, snapshots.NOW)
    assert len(graphs_of(bed.store, SUBJECT_BELIEF_GRAPH)) == 1 and bed.believes() == ("Dry", 0.05)


def test_a_samples_observation_is_believed_of_what_it_is_a_sample_of(monkeypatch, snapshots):
    """A probe in a patch of the pot: its observation is OF the patch, and what is believed is the pot's,
    the subject whose operating range judged it. The world the rules' sample case stands on says no
    words for its moisture and no step from a revision to a belief, so both are stated beside it."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(SAMPLE)
    put_document(store, document(RULES))
    words, steps = T + "words", T + "steps"
    update(store, f"""PREFIX : <{T}> PREFIX belief: <http://example.org/orexis/belief#>
INSERT DATA {{
  GRAPH <{steps}> {{ belief:RevisionGraph rdfs:subClassOf orexis:BeliefGraph .
                     sensing:SubjectBeliefGraph rdfs:subClassOf orexis:StateGraph , orexis:BeliefGraph , orexis:Graph }}
  GRAPH <{words}> {{ :moisture sensing:stateAs :soil ; sensing:valueAs :wetness ; sensing:belowAs :Dry ;
                                sensing:insideAs :Moist ; sensing:aboveAs :Wet }}
  {entry(store, steps, 'http://example.org/orexis#OntologyGraph', 'http://example.org/orexis#Asserted')}
  {entry(store, words, PUBLIC, 'http://example.org/orexis#Asserted')} }}""")
    (graph,) = received(store, snapshots.ME, T + "probe", b'{"value": 0.05}', snapshots.NOW)
    revise(store, graph, read=graphs_of(store, PUBLIC))
    (written,) = believe(store, snapshots.ME, graph)
    said = {(q.subject.value, q.predicate.value, q.object.value) for q in quads(store, written)}
    assert said == {(T + "zamioculcas", T + "soil", T + "Dry"), (T + "zamioculcas", T + "wetness", "0.05")}, said
