"""Taking a want away — tested where the function lives.

A want IS its graph (#645), so withdrawing one is dropping a graph and clearing what the
catalogue said of it. What is asserted is that nothing is left behind, which is the half of
the derivation's replace-whole that `forget_want` does on its own.
"""

from __future__ import annotations

from orexis.agent.store import bindings, query_over

from orexis.agent.planning.forget_wants import forget_want
from orexis.agent.planning.planner import find_wants


def test_forgetting_a_want_leaves_what_replacing_one_leaves(wants):
    """The two ways a want goes, held to leaving the same nothing.

    The derivation takes a want out and puts it back; `forget_want` does the first half and
    does not put it back. They share the text for that reason. What the catalogue says OF the
    graph is not in the graph, so a row left pointing at an empty one is litter every reader
    asking by class would still be handed — and a graph is taken away only when the want was
    the LAST in it, since a stretch is shared by whatever is in trouble over it.

    Announcing is nobody's here any more. These write the store and tell no one; whoever
    called says what changed, so a caller holding a projection can refresh it.
    """
    wants.derived()
    assert find_wants(wants.store, uri="urn:test:want") == ["urn:test:want"]

    forget_want(wants.store, "urn:test:want")
    assert find_wants(wants.store, uri="urn:test:want") == [], "the want is gone"
    graph = wants.graph_of()
    assert not bindings(query_over(wants.store, 
        f"SELECT ?p WHERE {{ <{graph}> ?p ?o }}", "urn:test:catalogue")), \
        "and the catalogue says nothing of its graph"
