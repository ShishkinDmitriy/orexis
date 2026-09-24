"""`register`: this layer's rules, put where the deliberator runs them.

The three rules that say which side of each of its subject's ranges an observation lies on
are a `sh:RuleSet` in `rules.ttl` beside this file. Registering them is loading that file into
a graph of the layer's own, classified `sh:RulesGraph` and asserted — the draft's kind, which
`revise` reads by and no other — so that every observation and every prediction the container
reports changed is concluded over by them. The container calls this at boot, and genesis 0.2.0
will load the packages' rule sets the same way; it is idempotent, since the graph is replaced
and the row restated.
"""

from __future__ import annotations

from pathlib import Path

from agent.store import classify, put_graph

from .ontology import ASSERTED, RULES_GRAPH, rules_graph

RULES = Path(__file__).with_name("rules.ttl")


def register(store) -> str:
    """Load this layer's rule set into its rules graph and say what the graph is. The name."""
    graph = rules_graph()
    put_graph(store, graph, RULES.read_text())
    classify(store, graph, RULES_GRAPH, ASSERTED)
    return graph
