"""`rules.ttl`: this layer's rule set, a document saying it is a `sh:RulesGraph`, put in the
store as a boot puts every document, and held — through the belief package's `revise`, which a
test here may import and the code may not — to what it concludes of a percept: what it is of, and
whether its sensor is stuck on one number.

STUCK IS A RULE OVER THE PERCEPTS KEPT (#462, #944): a sensor whose last `sensing:stuckAfter`
readings all gave one raw number is stuck on it, concluded in the revision of the percept arriving,
so it holds while that percept does, and the first reading whose number differs finds the kept ones
no longer agree. It counts READINGS, not time.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agent import clock
from agent.belief.revise import revise
from agent.ontology import BELIEF, KNOWN
from agent.belief.ontology import RULES_GRAPH
from agent.sensing.ontology import OBSERVATION_GRAPH, STUCK_AFTER_TERM
from agent.sensing.received import STUCK_AFTER, received
from agent.store import closed, document, graphs_of, put_document, revisions_of, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
BOARD = Path(__file__).parent / "worlds" / "a_board_and_its_peripherals.trig"
RULES = Path(__file__).parents[1] / "rules.ttl"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"
CADENCE = timedelta(seconds=900)


@pytest.fixture
def world(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(RULES))
    return store


def _read(store, sensor, value, at, me) -> list[str]:
    """`value` read by `sensor` at `at`, and each percept written revised as sensing has the deliberator
    revise it: beside the public graphs holding then, into this layer's kind."""
    written = received(store, me, sensor, f'{{"value": {value}}}'.encode(), at)
    for graph in written:
        revise(store, graph, read=graphs_of(store, *KNOWN, at=at), kind=OBSERVATION_GRAPH)
    return written


def _stuck(store, at) -> list[tuple[str, float]]:
    """Every sensor said stuck at `at`, and on what: read where the percept holding then is."""
    return [(r["sensor"].rsplit("#", 1)[-1], float(r["n"]))
            for r in rows(store, "SELECT ?sensor ?n WHERE { ?sensor sensing:stuckOn ?n }",
                          graphs_of(store, OBSERVATION_GRAPH, at=at, now=at))]


def _every_cadence(store, snapshots, numbers, start=None, sensor=PROBE):
    at = start or snapshots.NOW
    for number in numbers:
        _read(store, sensor, number, at, snapshots.ME)
        at += CADENCE
    return at - CADENCE


def test_the_rules_graph_is_the_drafts_kind_and_named_by_its_document(world):
    assert graphs_of(world, RULES_GRAPH) == [RULES.resolve().as_uri()]
    assert put_document(world, document(RULES)) == graphs_of(world, RULES_GRAPH), "put again, one graph"


def test_what_is_concluded_of_a_percept_is_a_percept_and_no_belief(world, snapshots):
    """The revision of a percept is of this layer's kind, handed by sensing as the runner of the
    revision, so what the rules conclude of what a sensor said — what it is of, its quantity — is
    handed to no reader the percept is not; and the kind is beneath `orexis:Graph` alone (#944)."""
    [graph] = _read(world, PROBE, 0.05, snapshots.NOW, snapshots.ME)
    [revision] = revisions_of(world, graph, kind=OBSERVATION_GRAPH)
    assert revisions_of(world, graph) == [], "no belief was concluded of a percept"
    assert rows(world, "SELECT ?f ?v WHERE { ?o sosa:hasFeatureOfInterest ?f ; sosa:hasSimpleResult ?v }", [revision])
    kinds = {r["k"] for r in rows(world, "SELECT ?k WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g a ?k } }", (), g=revision)}
    assert OBSERVATION_GRAPH in kinds and BELIEF not in kinds, kinds
    assert revision not in graphs_of(world, *KNOWN, at=snapshots.NOW) and graph not in graphs_of(world, *KNOWN, at=snapshots.NOW)
    assert closed(world, OBSERVATION_GRAPH) == sorted([OBSERVATION_GRAPH, "http://example.org/orexis#Graph"])


def test_a_samples_observation_is_of_the_sample(monkeypatch, snapshots):
    """A probe mounted in a patch of the pot — `sosa:isHostedBy` a `sosa:Sample` that
    `sosa:isSampleOf` it, the received case's world — is concluded an observation OF the patch."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    world = snapshots.stand_in(Path(__file__).parent / "worlds" / "a_probe_in_a_sample_of_the_pot.trig")
    put_document(world, document(RULES))
    [graph] = _read(world, PROBE, 0.05, snapshots.NOW, snapshots.ME)
    (of,) = rows(world, "SELECT ?f WHERE { ?o sosa:hasFeatureOfInterest ?f }", revisions_of(world, graph, kind=OBSERVATION_GRAPH))
    assert of["f"].endswith("#patch")


def test_stuck_holds_at_exactly_stuck_after_readings_of_one_number(world, snapshots):
    """#462: the probe gives 0.25 at every reading, on time. Through `STUCK_AFTER` - 1 readings nothing
    is said, since still soil and a frozen probe look alike for a while; at the `STUCK_AFTER`th the probe
    is stuck on its number, and a reading later it still is — said of the percept holding then, once."""
    last = _every_cadence(world, snapshots, [0.25] * (STUCK_AFTER - 1))
    assert _stuck(world, last) == [], f"{STUCK_AFTER - 1} readings of one number are short of the limit"
    tipped = _every_cadence(world, snapshots, [0.25], last + CADENCE)
    assert _stuck(world, tipped) == [("probe", 0.25)]
    assert _stuck(world, tipped - timedelta(seconds=1)) == [], "not before the reading that made it so"
    again = _every_cadence(world, snapshots, [0.25], tipped + CADENCE)
    assert _stuck(world, again) == [("probe", 0.25)], "said once, of the percept holding"


def test_the_first_reading_that_differs_ends_it(world, snapshots):
    last = _every_cadence(world, snapshots, [0.25] * STUCK_AFTER)
    assert _stuck(world, last)
    moved = _every_cadence(world, snapshots, [0.26], last + CADENCE)
    assert _stuck(world, moved) == [], "the kept readings no longer agree"
    last = _every_cadence(world, snapshots, [0.26] * (STUCK_AFTER - 2), moved + CADENCE)
    assert _stuck(world, last) == [], "the new number is counted from its first reading, and is one short"
    last = _every_cadence(world, snapshots, [0.26], last + CADENCE)
    assert _stuck(world, last) == [("probe", 0.26)]


def test_it_counts_readings_not_time(world, snapshots):
    """A sensor that misses readings is said stuck later than one that never misses: six readings of one
    number a day apart are six readings, and five an hour apart five."""
    at = snapshots.NOW
    for _ in range(STUCK_AFTER - 1):
        _read(world, PROBE, 0.25, at, snapshots.ME)
        at += timedelta(days=1)
    assert _stuck(world, at - timedelta(days=1)) == [], "five days of one number are five readings"
    _read(world, PROBE, 0.25, at, snapshots.ME)
    assert _stuck(world, at) == [("probe", 0.25)]


def test_a_number_a_count_apart_is_two_numbers(world, snapshots):
    """Identical means the raw number: a probe creeping by a count is alive to this rule, and the page
    says whose that case is."""
    last = _every_cadence(world, snapshots, [1330 + (n % 2) for n in range(STUCK_AFTER + 2)])
    assert _stuck(world, last) == []


def test_a_silence_ends_it(world, snapshots):
    """Stuck is said of the percept holding, so a sensor whose latest percept has ended — its next
    reading overdue past the grace — is said stuck no longer, as it has no present at all."""
    last = _every_cadence(world, snapshots, [0.25] * STUCK_AFTER)
    assert _stuck(world, last + 2 * CADENCE - timedelta(seconds=1)) == [("probe", 0.25)]
    assert _stuck(world, last + 2 * CADENCE) == []


def test_a_sensor_stating_no_frequency_is_never_said_stuck(monkeypatch, snapshots):
    """The board's probe states no frequency, so its silence is never said, and nor is its number:
    the world made no promise that its readings are samples on a cadence."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BOARD)
    put_document(store, document(RULES))
    at = snapshots.NOW
    for _ in range(STUCK_AFTER + 2):
        for graph in received(store, snapshots.ME, PROBE, b'{"soil": {"moisture": 0.2}}', at):
            revise(store, graph, read=graphs_of(store, *KNOWN, at=at), kind=OBSERVATION_GRAPH)
        at += timedelta(days=1)
    assert _stuck(store, at - timedelta(days=1)) == []


def test_the_stuck_limit_is_the_agents_where_its_self_graph_states_one(monkeypatch, snapshots):
    """The keeper's self graph says `sensing:stuckAfter 2`, a stance: the probe's number, given twice, is
    stuck where the figure in code would have waited six — read by the rule off the self graph, and by
    `received` for how many to keep, alike."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stating(snapshots.stand_in(WORLD), {STUCK_AFTER_TERM: 2})
    put_document(store, document(RULES))
    first = _every_cadence(store, snapshots, [0.25])
    assert _stuck(store, first) == [], "one reading is short of two"
    second = _every_cadence(store, snapshots, [0.25], first + CADENCE)
    assert _stuck(store, second) == [("probe", 0.25)]
