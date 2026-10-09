"""`rules.ttl`: this layer's rule set, a document saying it is a `sh:RulesGraph`, put in the
store as a boot puts every document, and held — through the belief package's `revise`, which a
test here may import and the code may not — to what it concludes of an observation against its
subject's ranges.
"""

from __future__ import annotations

from datetime import timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import KNOWN
from agent.belief.ontology import RULES_GRAPH
from agent.sensing.ontology import ABOVE, BELOW, INSIDE
from agent.sensing.received import received
from agent.store import document, graphs_of, put_document, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
RULES = Path(__file__).parents[1] / "rules.ttl"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"

_SIDES_Q = "SELECT ?p ?range WHERE { GRAPH $g { ?obs ?p ?range VALUES ?p { sensing:below sensing:inside sensing:above } } }"


def _sides(store, graph: str) -> set[tuple[str, str]]:
    return {(r["p"].rsplit("#", 1)[-1], r["range"].rsplit("#", 1)[-1])
            for r in rows(store, _SIDES_Q, (), g=graph + "/revisions")}


@pytest.fixture
def world(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(RULES))
    return store


def _read(store, snapshots, sensor, value: float) -> str:
    [graph] = received(store, snapshots.ME, sensor, f'{{"value": {value}}}'.encode(), snapshots.NOW)
    revise(store, graph, read=graphs_of(store, *KNOWN, at=snapshots.NOW))
    return graph


def test_the_rules_graph_is_the_drafts_kind_and_named_by_its_document(world):
    assert graphs_of(world, RULES_GRAPH) == [RULES.resolve().as_uri()]
    assert put_document(world, document(RULES)) == graphs_of(world, RULES_GRAPH), "put again, one graph"


def test_a_reading_under_the_floor_is_below_the_operating_range_and_inside_the_survival_one(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.05)
    assert _sides(world, graph) == {("below", "zamioculcas.operating"), ("inside", "zamioculcas.survival"), ("inside", "probe.operating")}


def test_a_reading_inside_is_inside_every_range(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.2)
    assert {p for p, _ in _sides(world, graph)} == {"inside"}


def test_a_reading_over_the_ceiling_is_above(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.5)
    assert _sides(world, graph) == {("above", "zamioculcas.operating"), ("above", "zamioculcas.survival"), ("inside", "probe.operating")}


def test_a_bound_is_inside(world, snapshots):
    graph = _read(world, snapshots, PROBE, 0.1)
    assert ("inside", "zamioculcas.operating") in _sides(world, graph)


def test_a_samples_observation_is_judged_by_its_subjects_ranges(monkeypatch, snapshots):
    """A probe mounted in a patch of the pot — `sosa:isHostedBy` a `sosa:Sample` that
    `sosa:isSampleOf` it, the received case's world — is concluded an observation OF the patch,
    and is judged by the pot's ranges."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    world = snapshots.stand_in(Path(__file__).parent / "worlds" / "a_probe_in_a_sample_of_the_pot.trig")
    put_document(world, document(RULES))
    graph = _read(world, snapshots, PROBE, 0.05)
    (of,) = rows(world, "SELECT ?f WHERE { GRAPH $g { ?o sosa:hasFeatureOfInterest ?f } }", (), g=graph + "/revisions")
    assert of["f"].endswith("#patch")
    assert ("below", "zamioculcas.operating") in _sides(world, graph)


#  THE POT'S OPERATING RANGE MOVED TO A BED'S, 0.30 to 0.60, stating a margin of 0.0002 — twice
#  what the simulator's probe strays either way — or stating none.
BED = ("schema:maxValue 0.3 ; schema:minValue 0.1 ; ssn:forProperty :moisture",
       "orexis:margin 0.0002 ; schema:maxValue 0.6 ; schema:minValue 0.3 ; ssn:forProperty :moisture")


def _bed(snapshots, margin: bool):
    text = WORLD.read_text()
    assert BED[0] in text
    store = snapshots.stand_in(WORLD, text.replace(BED[0], BED[1] if margin else BED[1].replace("orexis:margin 0.0002 ; ", "")))
    put_document(store, document(RULES))
    return store


def _judged(store, snapshots, values) -> list[str]:
    """Each value received a cadence after the last and revised, as a pass does — so each reading
    carries what the rules concluded of the one before — and the side of the bed's range each is on."""
    out, at = [], snapshots.NOW
    for value in values:
        [graph] = received(store, snapshots.ME, PROBE, f'{{"value": {value}}}'.encode(), at)
        revise(store, graph, read=graphs_of(store, *KNOWN, at=at))
        said = [p for p, r in _sides(store, graph) if r == "zamioculcas.operating"]
        assert len(said) == 1, (value, said)
        out.append(said[0])
        at += timedelta(minutes=15)
    return out


#  ACROSS THE FLOOR BY A TEN-THOUSANDTH EACH WAY, then clear of the floor and its margin, then down.
STRAYING = [0.3001, 0.2999, 0.3001, 0.2999, 0.3001, 0.3002, 0.3001, 0.2999]


@pytest.mark.parametrize("margin, sides", [
    (True, ["inside", "below", "below", "below", "below", "inside", "inside", "below"]),
    (False, ["inside", "below", "inside", "below", "inside", "inside", "inside", "below"]),
], ids=["margin", "none"])
def test_a_reading_straying_across_the_floor_reads_below_until_it_clears_the_margin(monkeypatch, snapshots, margin, sides):
    """Starting inside, the first reading under the floor is below at once; with the margin every
    reading after it is below until one reaches 0.3002, and the next under the floor is below again.
    Stating none, a side is the bare comparison it always was, and flips at every crossing."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    assert _judged(_bed(snapshots, margin), snapshots, STRAYING) == sides


@pytest.mark.parametrize("margin", [True, False], ids=["margin", "none"])
def test_a_real_drop_reads_below_at_once(monkeypatch, snapshots, margin):
    """A reading coming from inside crosses at the floor itself: the margin delays nothing."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    assert _judged(_bed(snapshots, margin), snapshots, [0.45, 0.25, 0.2999]) == ["inside", "below", "below"]


@pytest.mark.parametrize("margin, sides", [
    (True, ["inside", "above", "above", "inside", "inside"]),
    (False, ["inside", "above", "inside", "inside", "inside"]),
], ids=["margin", "none"])
def test_a_reading_straying_across_the_ceiling_reads_above_until_it_clears_the_margin(monkeypatch, snapshots, margin, sides):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    assert _judged(_bed(snapshots, margin), snapshots, [0.5999, 0.6001, 0.5999, 0.5998, 0.5999]) == sides
