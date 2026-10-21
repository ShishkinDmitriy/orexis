"""`mint`: the secret an agent draws its numbers from, minted once where it states none and never said; a
secret the self graph states is kept, which is how a test fixes every draw."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox

from agent.coordination.mint import mint
from agent.coordination.ontology import secret_graph
from agent.runtime import boot
from agent.ontology import BELIEF
from agent.store import graphs_of, rows

L = "http://example.org/orexis/world/lane#"
A, B, VAN_A, VAN_B = L + "courier_a", L + "courier_b", L + "van_a", L + "van_b"
TWO_VANS = "http://example.org/orexis/courier#no_two_vans_at_one_position"

LANE = Path(__file__).resolve().parents[3] / "world" / "lane"
_SECRET_Q = "SELECT ?s WHERE { $me coordination:secret ?s }"


def test_a_secret_is_minted_once_where_the_agent_states_none():
    store = boot(LANE, "courier_a")
    assert not rows(store, _SECRET_Q, graphs_of(store, BELIEF), me=A)
    assert mint(store, A) == [secret_graph(A)]
    (secret,) = [r["s"] for r in rows(store, _SECRET_Q, [secret_graph(A)], me=A)]
    assert len(secret) == 64 and int(secret, 16) >= 0, "two hundred and fifty-six random bits, in hex"
    assert mint(store, A) == [], "and kept"


def test_a_secret_the_self_graph_states_is_kept(meeting):
    store = meeting.store(A)
    assert {r["s"] for r in rows(store, _SECRET_Q, graphs_of(store, BELIEF), me=A)} == {"1" * 64}, "the self graph's, and no other"
    assert not list(store.quads_for_pattern(None, None, None, ox.NamedNode(secret_graph(A)))), "nothing minted"
