"""Where a wait lands — tested where the function lives (#920).

The claim: the ground after the one a world stands in begins at the least start of any ground later
than the world's own, and there is none after the last. Asked of a ground and of a possible world
alike, by the start each carries on its row.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.store import graphs_of, update
from agent.planning.lay_ground import lay_ground
from agent.planning.next_ground import next_ground
from agent.planning.ontology import GROUND_GRAPH
from agent.planning.prepare_ground import prepare_ground

CASE = Path(__file__).parent / "derive_wants" / "a_tank_low_now_refilled_later.trig"


@pytest.fixture
def imagined(monkeypatch, snapshots):
    """The refilled tank's imaginarium: two grounds, the present at noon and the refill at one."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = prepare_ground(snapshots.stand_in(CASE), ox.Store())
    lay_ground(store, snapshots.NOW)
    return store


def _a_world_from(store, name: str, start) -> str:
    """A possible world's row and nothing else: its period, starting at `start`."""
    update(store, f"""INSERT {{ GRAPH ?cat {{ <{name}> a planning:PossibleGraph ;
        dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start "{start.isoformat()}"^^xsd:dateTime ;
                                                    orexis:end "{start.isoformat()}"^^xsd:dateTime ] }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }}""")
    return name


def test_a_ground_is_followed_by_the_next_and_the_last_by_nothing(imagined, snapshots):
    present, later = sorted(graphs_of(imagined, GROUND_GRAPH))
    assert next_ground(imagined, present) == snapshots.NOW + timedelta(hours=1)
    assert next_ground(imagined, later) is None, "nothing is laid after the refill: nothing to wait for"


def test_a_forecast_the_search_reads_nothing_of_lays_no_ground_a_wait_could_land_in(monkeypatch, snapshots):
    """Laid where the texts read a predicate nothing states: the refill says nothing the search reads, so
    it is not where the search can be, lays no ground (#987, #992), and a wait has nothing to land in —
    the present is the one ground, followed by nothing."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = prepare_ground(snapshots.stand_in(CASE), ox.Store())
    (present,) = lay_ground(store, snapshots.NOW, within=frozenset({"http://example.org/test#unread"}))
    assert next_ground(store, present) is None, "the refill moves nothing the search reads"


def test_a_world_inside_a_ground_is_followed_by_the_ground_after_it(imagined, snapshots):
    """A world half an hour in stands in the present ground, and the refill's is the next; one a
    minute past the refill stands in the last."""
    inside = _a_world_from(imagined, "urn:test:inside", snapshots.NOW + timedelta(minutes=30))
    past = _a_world_from(imagined, "urn:test:past", snapshots.NOW + timedelta(hours=1, minutes=1))
    assert next_ground(imagined, inside) == snapshots.NOW + timedelta(hours=1)
    assert next_ground(imagined, past) is None
