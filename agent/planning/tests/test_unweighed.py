"""What is still to be weighed — tested where the read lives, over the low tank as a pass
stands at each of its steps."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.planning.admit import admit
from agent.planning.derive_wants import derive_wants
from agent.planning.find_wants import find_wants
from agent.planning.lay_ground import lay_ground
from agent.planning.prepare_ground import prepare_ground
from agent.planning.unweighed import unweighed
from agent.planning.weigh import weigh

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


def test_a_want_minted_now_is_offered_in_the_present_ground_only(store, snapshots):
    _sweep(store)
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    (pair,) = unweighed(store)
    assert pair["for"] == want and "/ground/" in pair["about"] and not pair.get("from")


def test_a_want_is_offered_in_the_ground_holding_at_its_instant(store, snapshots):
    """#858: a want minted for a foreseen instant is weighed in the ground holding then — the latest
    begun by its instant — and not in the present, where it read met and was withdrawn in the pass
    that minted it. A want with no period, and one whose instant every ground is past, root at the
    present: the present outranks the instant. Grounds and wants are written by hand here, since the
    read is about their rows alone."""
    from datetime import timedelta

    from agent.store import catalogue_of, update

    _sweep(store)
    now, cat = snapshots.NOW, catalogue_of(store)
    stamp = lambda t: f'"{t.isoformat()}"^^xsd:dateTime'
    grounds = {"later": now + timedelta(hours=1), "latest": now + timedelta(hours=2)}
    wants = {"foreseen": now + timedelta(hours=1, minutes=30), "passed": now - timedelta(hours=1), "timeless": None}
    catalogue = "".join(
        f"<urn:ground:{n}> a planning:GroundGraph , orexis:Graph ; "
        f"dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start {stamp(t)} ] .\n" for n, t in grounds.items()
    ) + "".join(
        f"<urn:wants:{n}> a planning:WantGraph , orexis:Graph"
        + (f" ; dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start {stamp(t)} ]" if t else "") + " .\n"
        for n, t in wants.items())
    held = " ".join(f"GRAPH <urn:wants:{n}> {{ <{snapshots.ME}> planning:holds <urn:want:{n}> . <urn:want:{n}> a planning:Want . }}"
                    for n in wants)
    update(store, f"INSERT DATA {{ GRAPH <{cat}> {{ {catalogue} }} {held} }}")
    offered = {p["for"]: p["about"] for p in unweighed(store) if p["for"].startswith("urn:want:")}
    present = offered["urn:want:timeless"]
    assert "/ground/" in present and "urn:ground" not in present, "no period: the earliest ground, the present"
    assert offered["urn:want:passed"] == present, "an instant every ground is past: the present"
    assert offered["urn:want:foreseen"] == "urn:ground:later", "the latest ground begun by its instant"
    assert len([p for p in unweighed(store) if p["for"].startswith("urn:want:")]) == 3, "one ground per want"


def test_a_candidate_leaving_a_weighed_world_is_offered_with_what_it_reached(store, snapshots):
    _sweep(store)
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    (root,) = _sweep(store)
    admit(store, root["about"])
    (pair,) = unweighed(store)
    from agent.store import Raw, rows
    assert pair["for"] == want and pair["from"] == root["about"]
    assert rows(store, "SELECT ?c WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $c a planning:Candidate } BIND($c AS ?c) }",
                (), c=Raw(f"<{pair['about']}>")), "what is offered is the candidate, said by its row"
    assert not pair.get("child"), "not yet taken"


def test_the_read_narrows_to_a_want_and_to_a_world(store, snapshots):
    """What an iteration asks: the candidates leaving the world it opens, for its want."""
    _sweep(store)
    derive_wants(store, snapshots.NOW)
    (want,) = find_wants(store, snapshots.NOW)
    (root,) = _sweep(store)
    admit(store, root["about"])
    assert unweighed(store, for_=want, leaving=root["about"]) == unweighed(store)
    assert unweighed(store, for_="urn:test:nobody") == []
    assert unweighed(store, leaving="urn:test:nowhere") == []
