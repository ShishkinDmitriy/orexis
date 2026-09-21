"""A graph says which stretch it HOLDS DURING, and the door honours it.

`knowledge/decisions/a-graph-holds-during-a-stretch.md`: a class is not temporal and
knowledge about instances is, so the stretch a saying is about belongs to the graph it is said in —
read at the door, where a reader is HANDED a scope, and never by a rule, which would be the
`now()` this project has just spent three changes removing.

The range is said in `graph/periods`, outside the default union and beside the provenance
graph, because a period CHANGES: a statement in a merged graph is a fact in every possible
world, so one that lapsed would move the invariant signature and kill a kept cone.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from conftest import genesis_store
from orexis_agent_progression.ontology import ACTIONS_GRAPH, WORLD_GRAPH
from orexis_agent_progression.ontology import PUBLIC

def _now() -> datetime:
    """Read per test, never once per module: an instant captured at import is a minute old by
    the time a loaded suite reaches the body, and every window here is measured from it."""
    return datetime.now(timezone.utc)


def _store():
    return genesis_store(world="loner")


def _say(st, graph: str, until=None, since=None) -> None:
    """What a graph says about itself, said where mentions of graphs live — one
    `dcterms:PeriodOfTime`, either end open: Dublin Core's own class for an interval named by
    its start and end dates, with the two properties DCMI never defined."""
    bounds = []
    if since is not None:
        bounds.append(f'orexis:start "{since.isoformat()}"^^xsd:dateTime')
    if until is not None:
        bounds.append(f'orexis:end "{until.isoformat()}"^^xsd:dateTime')
    st.update(f"""INSERT DATA {{ GRAPH <{st.catalogue}> {{
        <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ; {' ; '.join(bounds)} ] }} }}""")


def test_a_store_that_states_no_range_is_the_store_it_always_was():
    """Absent means always, on both sides — which is what every graph meant before the term
    existed, and what a vocabulary graph means for ever. The fast path is the ordinary one."""
    now = _now()
    st = _store()
    assert st.periods() == {}
    #  NOT A COUNT. It was `== 8`, which meant "the public graphs, as many as there are today"
    #  and went red the day the asserted graph became two — a graph of desires and a graph of
    #  wants — for a test about periods. `orexis:PublicGraph` is a class and `graphs_of` asks
    #  (AGENTS.md); what this needs is that the answer is not EMPTY, since the equality below
    #  would hold between two empty sets and say nothing.
    assert st.graphs_of(PUBLIC, at=now), "the door answers with the public graphs"
    assert st.graphs_of(PUBLIC, at=now) == st.graphs_of(PUBLIC, at=now + timedelta(days=365))


def test_a_graph_outside_its_range_is_not_merged():
    """The door drops it, and nothing else changes: an unqualified pattern stops seeing what
    the graph holds, because what an unqualified pattern reads IS the merge."""
    now = _now()
    st = _store()
    before = len(st.query("SELECT ?s WHERE { ?s a orexis:Agent }", st.graphs_of(PUBLIC, at=now))["results"]["bindings"])
    assert before, "the world names an agent while it is worth believing"

    _say(st, WORLD_GRAPH, until=now - timedelta(seconds=1))

    assert WORLD_GRAPH not in st.graphs_of(PUBLIC, at=now)
    assert st.query("SELECT ?s WHERE { ?s a orexis:Agent }", st.graphs_of(PUBLIC, at=now))["results"]["bindings"] == [], \
        "a graph past its range still answered an ordinary query"
    assert st.query(f"SELECT ?s WHERE {{ GRAPH <{WORLD_GRAPH}> {{ ?s a orexis:Agent }} }}", st.graphs_of(PUBLIC, at=now)
                    )["results"]["bindings"], \
        "naming a graph still reads it — lapsing is not forgetting, and a sweep is a decision"


def test_the_instant_is_the_askers_and_a_pass_says_which():
    """`at` is the whole of what keeps this out of a search's way. A pass reads one clock at
    its desire; without saying so it would watch a graph expire between two forks, and two worlds
    would differ by how long the agent had been thinking."""
    now = _now()
    st = _store()
    _say(st, ACTIONS_GRAPH, until=now + timedelta(minutes=1))

    assert ACTIONS_GRAPH in st.graphs_of(PUBLIC, at=now)
    assert ACTIONS_GRAPH in st.graphs_of(PUBLIC, at=now)
    assert ACTIONS_GRAPH not in st.graphs_of(PUBLIC, at=now + timedelta(minutes=2))
    assert ACTIONS_GRAPH in st.graphs_of(PUBLIC, at=now - timedelta(days=1)), \
        "an open start means always, so yesterday is inside the range too"


def test_a_graph_not_yet_valid_is_not_merged_either():
    """A forecast is the case this exists for: facts holding over a period the agent has not
    reached, which must not answer a question about now."""
    now = _now()
    st = _store()
    _say(st, ACTIONS_GRAPH, since=now + timedelta(hours=3), until=now + timedelta(hours=6))

    assert ACTIONS_GRAPH not in st.graphs_of(PUBLIC, at=now)
    assert ACTIONS_GRAPH in st.graphs_of(PUBLIC, at=now + timedelta(hours=4))
    assert ACTIONS_GRAPH not in st.graphs_of(PUBLIC, at=now + timedelta(hours=7))


def test_the_table_is_remembered_and_a_write_drops_it():
    """Remembered like everything else the store learns by asking, and the TABLE rather than a
    filtered list: which graphs now depends on when it is asked, and the table does not."""
    now = _now()
    st = _store()
    _say(st, ACTIONS_GRAPH, until=now + timedelta(minutes=1))
    assert st.periods() and st._catalogue_index is not None

    st.update("INSERT DATA { GRAPH <http://example.org/orexis/graph/sensed> { <urn:a> <urn:b> <urn:c> } }")
    assert st._catalogue_index is None, "a write drops what was learned by asking"
    assert ACTIONS_GRAPH in st.periods(), "and asking again learns it back"


def test_a_bound_nobody_can_read_does_not_drop_a_graph():
    """Not knowing is maximal everywhere here, and this is the same rule read the safe way
    round: a graph whose range is unreadable stays, rather than vanishing silently."""
    st = _store()
    st.update(f"""INSERT DATA {{ GRAPH <{st.catalogue}> {{ <{ACTIONS_GRAPH}> dcterms:temporal
        [ a dcterms:PeriodOfTime ; orexis:end "whenever"^^xsd:dateTime ] }} }}""")

    assert st.periods()[ACTIONS_GRAPH] == (None, None)
    assert ACTIONS_GRAPH in st.graphs_of(PUBLIC)


def test_a_range_on_a_graph_nobody_types_adds_nothing():
    """`graph/periods` says WHEN, never WHETHER: what is merged is still what the
    vocabulary types as public, and a range on something else is a statement about
    nothing this door has to answer for."""
    now = _now()
    st = _store()
    #  BEFORE AND AFTER, which is what "adds nothing" says. A literal count said it only for
    #  as long as the number held, and the number is a fact about the vocabulary rather than
    #  about periods — this test's subject.
    before = st.graphs_of(PUBLIC, at=now)
    _say(st, "http://example.org/orexis/graph/nowhere", until=now + timedelta(days=1))

    assert st.graphs_of(PUBLIC, at=now) == before
