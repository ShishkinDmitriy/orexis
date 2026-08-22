"""The desires store: what an agent pursues, as a store of its own (a-store-is-a-modality).

An agent HOLDS its stores — `agent.store`, `agent.desires_store`, the rest as #299 lands —
with no object between, by the sovereign's ruling: nothing ever addresses the collection.

Part 1 of #298: the store exists, is built at boot from the graphs the catalog types with a
desire modality, is read-only to everything the runtime holds, and is rebuilt — never edited —
when a premise moves. The reader migration (the split queries #296 measured) is the rest.
"""

from __future__ import annotations

import pytest

from agent.ontology import (AG, SENSED_GRAPH, WORLD_GRAPH, beliefs_graph)
from agent.store import ReadOnly, bindings

from conftest import build_agent, genesis_store

MOISTURE = "http://example.org/agora/water#SoilMoisture"


def _graphs_in(desires) -> set[str]:
    return {r["g"] for r in bindings(desires.query_union(
        "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"))}


def test_the_desires_store_holds_wants_and_only_wants(monkeypatch):
    """Selection is by CLASS, not by list: every graph the catalog types with a desire
    modality is copied — the derived regions, and the picks, since `ag:BeliefsGraph` is typed
    `ag:DesireGraph` and the sovereign's ruling made that literal — and nothing else is.
    A reading or a world fact in the desires store would be the modality split failing on
    day one."""
    agent = build_agent("gardener", genesis_store(world="loner"), monkeypatch)

    graphs = _graphs_in(agent.desires_store)
    assert any("constraint" in g for g in graphs), "the derived regions are wants"
    assert beliefs_graph("gardener") in graphs, "the picks are wants, by the ruling"
    assert WORLD_GRAPH not in graphs, "topology is a belief, not a want"
    assert SENSED_GRAPH not in graphs, "a reading is a belief, not a want"


def test_a_region_is_readable_from_the_desires_store_alone(monkeypatch):
    """The read surface deliberation is moving to: a desire shape answerable without the
    belief base in the room — the shapes half of every split #296 measured."""
    agent = build_agent("gardener", genesis_store(world="loner"), monkeypatch)

    rows = bindings(agent.desires_store.query_union(f"""
        SELECT ?low ?high WHERE {{
          ?region ssn:forProperty <{MOISTURE}> ; sh:property ?below , ?above .
          ?below sh:severity ag:ShouldBecome ; ag:violationIs ag:Below ;
                 sh:qualifiedValueShape/sh:property/sh:maxExclusive ?low .
          ?above sh:severity ag:ShouldBecome ; ag:violationIs ag:Above ;
                 sh:qualifiedValueShape/sh:property/sh:minExclusive ?high .
        }}"""))
    assert rows, "the gardener's moisture region must be in the desires store"
    assert float(rows[0]["low"]) < float(rows[0]["high"])


def test_nothing_an_agent_runs_can_write_into_it(monkeypatch):
    """#298's second done-when, enforced by the handle: the read half has no update, no
    clear and no load — misuse fails at the call site as `AttributeError`, not as a
    discipline someone forgot to follow."""
    agent = build_agent("gardener", genesis_store(world="loner"), monkeypatch)

    assert isinstance(agent.desires_store, ReadOnly)
    for writer in ("update", "clear_graph", "load_file", "put_graph", "endow_graph"):
        with pytest.raises(AttributeError):
            getattr(agent.desires_store, writer)


def test_recomputation_is_the_only_write_path(monkeypatch):
    """A premise moves, the store is REBUILT, and the change appears — while the old handle's
    copy never saw it, which is what 'a copy, alive until the next rebuild' means. Nothing
    retracted the old state and nothing edited the new one in place."""
    st = genesis_store(world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    before = agent.desires_store

    constraint = next(g for g in _graphs_in(before) if "constraint" in g)
    marker = f"<{AG}test_premise> a <{AG}Modality> ."
    st.update(f"INSERT DATA {{ GRAPH <{constraint}> {{ {marker} }} }}")

    ask = f"ASK {{ <{AG}test_premise> ?p ?o }}"
    assert not before.query_union(ask)["boolean"], "a copy must not see later writes"
    agent.rebuild_desires()
    assert agent.desires_store.query_union(ask)["boolean"], \
        "a rebuild reads the premises as they now stand"
