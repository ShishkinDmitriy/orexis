"""`holdings`: what an agent says of its own future under a constraint — its things' values on the constraint's
key, now and after each change its walking plans make, each over the period it holds; the key read off the
constraint's own text."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox

from agent.coordination.holdings import Holding, _key, holdings

L = "http://example.org/orexis/world/lane#"
A, B, VAN_A, VAN_B = L + "courier_a", L + "courier_b", L + "van_a", L + "van_b"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"

COURIER = "http://example.org/orexis/courier#"
X, Y = COURIER + "x", COURIER + "y"
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

_TWO_VANS = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT $this ?value WHERE { $this a courier:Van ; courier:x ?x ; courier:y ?y .
                            ?value a courier:Van ; courier:x ?x ; courier:y ?y . FILTER(?value != $this) }"""
_ONE_VAN = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT $this WHERE { $this a courier:Van ; courier:x ?x . FILTER(?x > 6) }"""


def test_the_key_is_what_two_subjects_of_the_constraint_join_on():
    assert _key(_TWO_VANS) == frozenset({X, Y})
    assert _key(_ONE_VAN) == frozenset(), "one subject joins nothing: no resource two agents can both want"
    assert _key("this will not parse") == frozenset()


def test_two_holdings_meet_at_the_same_values_over_periods_that_overlap():
    at = ((X, ox.Literal("3", datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer"))),)
    elsewhere = ((X, ox.Literal("4", datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer"))),)
    now = Holding(VAN_A, at, None, T0 + timedelta(seconds=30))
    later = Holding("b", at, T0 + timedelta(seconds=20), None)
    after = Holding("b", at, T0 + timedelta(seconds=30), None)
    assert now.overlaps(later) and later.overlaps(now)
    assert not now.overlaps(after), "one ends as the other begins"
    assert not now.overlaps(Holding("b", elsewhere, None, None)), "other values"


def test_a_van_holds_its_cell_now_and_each_cell_its_walking_plan_drives_it_to(meeting):
    held = holdings(meeting.store(A), TWO_VANS, meeting.at)
    assert held and {h.thing for h in held} == {VAN_A}, held
    assert {p for h in held for p, _ in h.values} == {X, Y}, "the key's values and nothing else of the plan"
    now, *ahead = held
    assert now.start is None and now.end is not None, "now, until the first change lands at the latest"
    assert ahead and all(h.start is not None for h in ahead)
    assert [h.start for h in ahead] == sorted(h.start for h in ahead), "in the order they are walked"
    assert ahead[-1].end is None, "the last holds on"
    assert all(a.values != b.values for a, b in zip(held, held[1:])), "each a change of the key"
