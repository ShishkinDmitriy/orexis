"""The deliberation layer's own namespace (#529): the trace's words and the budget carry it.
Declared here — never in progression's term module — since a lower layer may not spell a
higher one's vocabulary."""
from __future__ import annotations

DELIBERATION = "http://example.org/orexis/deliberation#"

#  A REMEMBERED PLAN (#469): a plan that worked, lifted into the agent's own graph and hung
#  on the want it served, adopted again without a search where its regressed precondition holds (#551).
REMEMBERED_PLAN = DELIBERATION + "RememberedPlan"
FOR_WANT = DELIBERATION + "forWant"
LIFTED = DELIBERATION + "lifted"
MEASURED_COST = DELIBERATION + "measuredCost"
REMEMBERED_AT = DELIBERATION + "rememberedAt"


def remembered_graph(agent_id: str) -> str:
    """ONE agent's remembered plans: a recorded graph, disclosed like the ledger."""
    return "http://example.org/orexis/graph/remembered/" + agent_id


def pursued_graph(agent_id: str) -> str:
    """ONE agent's pursued wants (#618): the wants derived under its `orexis:Desire` roots while
    they read unmet — a recorded graph the desire modality projects, disclosed like the ledger."""
    return "http://example.org/orexis/graph/pursued/" + agent_id


#  A JUDGMENT (judge-desires-then-derive-wants): what a desire's met-test read at an instant,
#  in SHACL's words for a report, `deliberation:judges` the desire.
JUDGMENT = DELIBERATION + "Judgment"
JUDGES = DELIBERATION + "judges"
CONSTRAINT = DELIBERATION + "constraint"


def judgments_graph(agent_id: str) -> str:
    """ONE agent's judgments, replaced whole on every run of `judge_desires`: a working
    graph, read by `derive_wants` and by eyes, carried by no plan and recorded by nothing."""
    return "http://example.org/orexis/graph/judgments/" + agent_id


#  A SCOPE (clusterise-actions): which predicates some one action or derivation moves together.
SCOPE = DELIBERATION + "Scope"
IN_SCOPE = DELIBERATION + "inScope"


def scopes_graph(agent_id: str) -> str:
    """ONE agent's scopes, replaced whole on every run of `clusterise_actions`: a working
    graph, read by `derive_wants` and by eyes, carried by no plan and recorded by nothing."""
    return "http://example.org/orexis/graph/scopes/" + agent_id
