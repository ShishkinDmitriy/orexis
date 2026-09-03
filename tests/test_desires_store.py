"""The desires store: what an agent pursues, as a store of its own (a-store-is-a-modality).

An agent HOLDS its stores — `agent.beliefs`, `agent.desires`, the rest as #299 lands —
with no object between, by the sovereign's ruling: nothing ever addresses the collection.

Part 1 of #298: the store exists, is built at boot from the graphs the catalog types with a
desire modality, is read-only to everything the runtime holds, and is rebuilt — never edited —
when a premise moves. The reader migration (the split queries #296 measured) is the rest.
"""

from __future__ import annotations

import pytest

from orexis_agent_progression.ontology import (OREXIS, STATE_GRAPH, WORLD_GRAPH, beliefs_graph)
from orexis_agent_progression.store import bindings

from conftest import build_agent, genesis_store

MOISTURE = "http://example.org/orexis/water#SoilMoisture"


def _graphs_in(desires) -> set[str]:
    return {r["g"] for r in bindings(desires.query_union(
        "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"))}


def test_the_desires_store_holds_wants_and_only_wants(monkeypatch):
    """Selection is by CLASS, not by list: every graph the catalog types with a desire
    modality is copied — the derived regions, and the picks, since the pick record is typed
    `orexis:DesireGraph` and the sovereign's ruling made that literal — and nothing else is.
    A reading or a world fact in the desires store would be the modality split failing on
    day one."""
    agent = build_agent("gardener", genesis_store(world="loner"), monkeypatch)

    graphs = _graphs_in(agent.desires)
    assert any(g.endswith("desire/derived") for g in graphs), \
        "the regions are DERIVED here now — genesis derives no wants (#312)"
    assert beliefs_graph("gardener") in graphs, "the pick record is projected: picks are wants"
    assert WORLD_GRAPH not in graphs, "topology is a premise, dropped after the derivation"
    assert STATE_GRAPH not in graphs, "a reading is a belief, not a want"


def test_a_region_is_readable_from_the_desires_store_alone(monkeypatch):
    """The read surface deliberation is moving to: a desire shape answerable without the
    belief base in the room — the shapes half of every split #296 measured."""
    agent = build_agent("gardener", genesis_store(world="loner"), monkeypatch)

    rows = bindings(agent.desires.query_union(f"""
        SELECT ?low ?high WHERE {{
          ?desire orexis:metWhen ?region ; orexis:bindsWhen orexis:Always .
          ?region ssn:forProperty <{MOISTURE}> ; sh:property ?below , ?above .
          ?below orexis:violationIs orexis:Below ;
                 sh:qualifiedValueShape/sh:property/sh:maxExclusive ?low .
          ?above orexis:violationIs orexis:Above ;
                 sh:qualifiedValueShape/sh:property/sh:minExclusive ?high .
        }}"""))
    assert rows, ("the gardener's moisture region must be in the desires store — and the want "
                  "must state its scope (#472): the pattern walks orexis:bindsWhen on purpose, so "
                  "a derivation that stops writing one goes red here")
    assert float(rows[0]["low"]) < float(rows[0]["high"])


def test_nothing_an_agent_runs_can_write_into_it(monkeypatch):
    """#298's second done-when, enforced by the modality's own surface: read-only is the
    desire modality's DECISION, so the class exposes queries and no writer — misuse fails at
    the call site as `AttributeError`, not as a discipline someone forgot to follow."""
    agent = build_agent("gardener", genesis_store(world="loner"), monkeypatch)

    for writer in ("update", "clear_graph", "load_file", "put_graph", "endow_graph"):
        with pytest.raises(AttributeError):
            getattr(agent.desires, writer)


def test_recomputation_is_the_only_write_path(monkeypatch):
    """A premise moves, the modality is REBUILT, and the change appears — while a read
    surface captured before the rebuild still answers from the old copy, which is what 'a
    copy, alive until the next rebuild' means. Nothing retracted the old state and nothing
    edited the new one in place."""
    st = genesis_store(world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    stale = agent.desires.query_union   # the surface as it stands before the premise moves

    marker = f"<{OREXIS}test_premise> a <{OREXIS}Desire> ."
    st.update(f"INSERT DATA {{ GRAPH <{beliefs_graph('gardener')}> {{ {marker} }} }}")

    ask = f"ASK {{ <{OREXIS}test_premise> ?p ?o }}"
    assert not agent.desires.query_union(ask)["boolean"], "a copy must not see later writes"
    agent.desires.rebuild()
    assert agent.desires.query_union(ask)["boolean"], \
        "a rebuild reads the premises as they now stand"
    assert not stale(ask)["boolean"], \
        "the copy a rebuild replaced is unchanged — replaced, never edited"


ROOT = "http://example.org/orexis/world/loner#everything_tended_stays_alive"
GARDENER = "http://example.org/orexis/world/loner#gardener"
ASSERTED_GRAPH = "http://example.org/orexis/graph/desire/asserted"


def test_a_world_can_state_a_root_desire_and_an_amendment_can_retire_it(monkeypatch, tmp_path):
    """#264's ask, by the desires-store mechanism, plus the half that made it honest.

    A world file is TriG, so a world states a root desire by naming the graph it lands in and
    typing it in the same file — the catalog then calls it a desire graph arrived-by-Asserted,
    and the desires-store build copies it without any code learning the name. The second half
    is the amendment: a ratification that drops the desire must drop it EVERYWHERE, which is
    what `put_graph` clearing every file-named graph before reloading bought — loading is
    additive, and a quad store keeps what nobody removes.
    """
    import shutil

    from agent import genesis
    from orexis_agent_progression.store import Store

    src = genesis.world_dir("loner")
    dst = tmp_path / "asserted"
    shutil.copytree(src, dst)
    (dst / "desire.ttl").write_text(f"""@prefix orexis: <http://example.org/orexis#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

GRAPH <{ASSERTED_GRAPH}> {{
  <{GARDENER}> orexis:holds <{ROOT}> .
  <{ROOT}> a sh:NodeShape ;
      rdfs:comment "everything the gardener tends stays alive — the sentence somebody ratified" .
}}
""")
    st = Store()
    genesis.refresh_public(st, dst)
    genesis.birth(st, dst, "gardener")
    agent = build_agent("gardener", st, monkeypatch)

    ask = f"ASK {{ <{GARDENER}> orexis:holds <{ROOT}> }}"
    assert agent.desires.query_union(ask)["boolean"], \
        "the root desire must reach the desire modality"
    assert st.query(f"ASK {{ <{ASSERTED_GRAPH}> orexis:arrivedBy orexis:Asserted }}")["boolean"], \
        "and the kernel's own declaration says who put it there — a world file needs no typing line"

    # The amendment: the sovereign stops stating it, and the want is no longer implied —
    # nothing retracted it, it is simply absent from what the files now ratify.
    (dst / "desire.ttl").unlink()
    genesis.refresh_public(st, dst)
    agent.desires.rebuild()
    assert not agent.desires.query_union(ask)["boolean"], \
        "a want the ratification dropped must not survive it"


def test_a_commitment_survives_a_restart_in_its_own_room(monkeypatch, tmp_path):
    """The intention modality's row of the table, exercised where it is true: a volume.

    A pre-split volume is one store at the root; the first boot with rooms moves the belief
    base into its own, adopts any ledger written before intentions had a store, and a second
    opening finds the commitment still there — persistence is the volume's, whichever store
    holds the quads.
    """
    import pyoxigraph as ox

    from agent import genesis
    from orexis_agent_deliberation.beliefs import Beliefs
    from orexis_agent_progression.intentions import Intentions
    from orexis_agent_progression.store import Store
    from orexis_agent_progression.graphs import intentions_graph

    state = tmp_path / "state"
    world = genesis.world_dir("loner")

    # a pre-split life: one store at the volume root, a ledger entry in the belief base
    st = Store(str(state))
    genesis.refresh_public(st, world)
    genesis.birth(st, world, "gardener")
    st.update(f"""INSERT DATA {{ GRAPH <{intentions_graph("gardener")}> {{
        <urn:test:i1> a <http://example.org/orexis/progression#Intention> }} }}""")
    del st

    # first boot with rooms: layout migrates, the modality adopts the ledger
    st = Store(genesis._belief_room(str(state)))
    beliefs = Beliefs(st, "gardener")
    intentions = Intentions(str(state), beliefs)
    ask = "ASK { <urn:test:i1> ?p ?o }"
    assert intentions.query_union(ask)["boolean"], "the adopted commitment must be readable"
    assert not beliefs.query_union(ask)["boolean"], \
        "and gone from the belief base — moved, not copied"
    del intentions, beliefs, st

    # a restart: nothing re-adopts, the commitment is simply still there
    st = Store(genesis._belief_room(str(state)))
    intentions = Intentions(str(state), Beliefs(st, "gardener"))
    assert intentions.query_union(ask)["boolean"], "a commitment survives a restart"
