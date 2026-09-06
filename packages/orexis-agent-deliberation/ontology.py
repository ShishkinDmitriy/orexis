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
