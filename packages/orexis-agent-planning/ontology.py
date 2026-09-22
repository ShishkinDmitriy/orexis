"""The planning layer's own namespace (#529): the trace's words, the scopes and the budget
carry it. Declared here — never in the execution layer's term module — since a lower layer may
not spell a higher one's vocabulary.

ELEVEN TERMS, AND THE PREDECESSOR HAD FIFTY-FOUR. What is gone is the trace — everything a
pass recorded about itself for a reader — and the remembered plan, both read by code this layer
no longer has. A term nobody reads is annotation; they come back with their readers.
"""
from __future__ import annotations

PLANNING = "http://example.org/orexis/planning#"

def pursued_graph(agent_id: str) -> str:
    """ONE agent's pursued wants (#618): the wants derived under its `orexis:Desire` roots while
    they read unmet — a recorded graph the desire modality projects, disclosed like the ledger."""
    return "http://example.org/orexis/graph/pursued/" + agent_id


#  WHAT A PASS FINDS, per want: a graph of its own in the imaginarium, holding the steps in
#  the ledger's own words. Named by `imaginarium.plan_graph` and copied out by the execution
#  layer; nothing here is written to the belief base.
PLAN_GRAPH = PLANNING + "PlanGraph"
FOR_WANT = PLANNING + "forWant"


#  A DERIVATION (scope-actions): one INSERT of one loaded rule, as the edge it makes. Written
#  at every refresh of public knowledge, so the partition is a function of the store and not of
#  the files — the actions are in the store already and the rules were not.
DERIVATION = PLANNING + "Derivation"
READS = PLANNING + "reads"
WRITES = PLANNING + "writes"
ANYTHING = PLANNING + "Anything"
DERIVATION_GRAPH = PLANNING + "DerivationGraph"

#  THE ONE GRAPH INSTANCE THIS LAYER NAMES, and it is named because the vocabulary declares it
#  and genesis writes it: a public graph, spelled in the T-Box beside the class, as the world's
#  and the actions' are. Every reader asks the class.
DERIVATIONS_GRAPH = "http://example.org/orexis/graph/derivations"


#  A SCOPE (scope-actions): which predicates some one action or derivation moves together.
SCOPE = PLANNING + "Scope"


def scopes_graph() -> str:
    """THE STORE's scopes, replaced whole on every run of `scope_actions`: a working graph,
    read by `derive_wants` and by eyes, carried by no plan and recorded by nothing. Nobody's,
    and takes no id: the partition is a function of the actions the store holds and the
    derivations loaded, which are the same rows for everyone reading one store."""
    return "http://example.org/orexis/graph/scopes"
