"""What is still to be weighed — tested where the read lives, over the low tank as a pass
stands at each of its steps."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from orexis.agent import clock
from orexis.agent.planning.admit import admit
from orexis.agent.planning.derive_wants import derive_wants
from orexis.agent.planning.find_wants import find_wants
from orexis.agent.planning.lay_ground import lay_ground
from orexis.agent.planning.prepare_ground import prepare_ground
from orexis.agent.planning.unweighed import unweighed
from orexis.agent.planning.weigh import weigh

CASE = Path(__file__).parent / "plans" / "a_low_tank_is_filled.trig"


@pytest.fixture
def store(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    st = prepare_ground(snapshots.stand_in(CASE), ox.Store())
    lay_ground(st, snapshots.NOW)
    return st


def _sweep(store):
    pairs = unweighed(store)
    for pair in pairs:
        weigh(store, pair["for"], pair["about"])
    return pairs


def test_the_desires_in_the_grounds_come_first_and_go_once_weighed(store, snapshots):
    (pair,) = unweighed(store)
    assert pair["for"].endswith("#keeper.in_range") and "/ground/" in pair["about"]
    _sweep(store)
    assert unweighed(store) == [], "weighed, and not offered again"


def test_a_minted_want_is_offered_in_the_present_ground_only(store, snapshots):
    _sweep(store)
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    (pair,) = unweighed(store)
    assert pair["for"] == want and "/ground/" in pair["about"] and not pair.get("from")


def test_a_candidate_leaving_a_weighed_world_is_offered_with_what_it_reached(store, snapshots):
    _sweep(store)
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    (root,) = _sweep(store)
    admit(store, root["about"], snapshots.ME)
    (pair,) = unweighed(store)
    assert pair["for"] == want and pair["about"].endswith(".by") and pair["from"] == root["about"]
    assert not pair.get("child"), "not yet taken"


def test_the_read_narrows_to_a_want_and_to_a_world(store, snapshots):
    """What an iteration asks: the candidates leaving the world it opens, for its want."""
    _sweep(store)
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    (root,) = _sweep(store)
    admit(store, root["about"], snapshots.ME)
    assert unweighed(store, for_=want, leaving=root["about"]) == unweighed(store)
    assert unweighed(store, for_="urn:test:nobody") == []
    assert unweighed(store, leaving="urn:test:nowhere") == []
