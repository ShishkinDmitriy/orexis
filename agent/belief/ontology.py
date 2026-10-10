"""The belief package's own words, and the name it spells for eyes.

THE RULE VOCABULARY IS SHACL 1.2 INFERENCE RULES', ADOPTED AS IT STANDS: the graph in the role
of a rules graph, the rule set a package ships, the SPARQL rule with its construct, layer,
order, deactivation and run-once. Every one of those is spelled by the store's dictionary in a
text, and named here only for the two readers in Python. What is ours is the inference graph of
one source, which the draft names as a role and not a class, and what a rule that CHANGES a state
needs and the draft lacks: its delete and the kind whose arrival triggers a transition (`ontology.ttl`
beside this file). Where a transition writes is no word of ours: the runner prepares a state graph
for it, the kernel's `orexis:StateGraph`.

THE NAME IS FOR EYES. A source's revision graph and an arrival's state graph are spelled from the
source's own name; every reader asks the catalogue by class and by provenance, and
renaming one here would change nothing a reader sees.
"""

from __future__ import annotations

BELIEF = "http://example.org/orexis/belief#"
SH = "http://www.w3.org/ns/shacl#"

#  THE DRAFT'S OWN: the graph in the role of a rules graph, which `revise` reads by kind.
RULES_GRAPH = SH + "RulesGraph"

#  OURS: the graph of revisions — one per source — and whether its rules settled over it.
REVISION_GRAPH = BELIEF + "RevisionGraph"
SETTLED = BELIEF + "settled"

#  OURS, FOR WHAT CHANGES A STATE: a rule's delete, beside the draft's construct; and the kind whose
#  arrival triggers a transition.
DELETE = BELIEF + "delete"
TRIGGERED_BY = BELIEF + "triggeredBy"

#  HOW MANY RULE EXECUTIONS ONE PASS MAY SPEND: a stance the agent states of itself in its self
#  graph, read by the deliberator when it is made (knowledge/domain/kernel/stance.md).
BUDGET_TERM = BELIEF + "budget"

PROV = "http://www.w3.org/ns/prov#"
DERIVED_FROM = PROV + "wasDerivedFrom"


def revision_graph(source: str) -> str:
    """Where the revisions of `source` — what the rules conclude of it — are kept."""
    return source + "/revisions"


def state_graph(arrival: str) -> str:
    """Where what the transitions `arrival` triggered inserted is kept: the state graph the runner
    prepares for them, one per arrival."""
    return arrival + "/believed"
