"""The wallet, as a belief this agent keeps — what it has left, in its own graph.

**A balance that lived in memory was a belief the agent forgot.** `market:hasEndowment` is the
OPENING figure, authored at genesis; the running balance was a Python attribute decremented on a
claim and never written down, so a restart handed the agent its endowment back and it bid again
with money it had already spent. What an agent has left comes from outside its own reasoning —
the market decides it — which is the store column of
knowledge/decisions/model-it-only-if-a-plan-would-branch-on-it.md, and a plan branches on it
directly: `value_bid` sizes a bid by what the wallet can pay for.

Written the way every other belief a package keeps is: one row in the agent's own beliefs graph,
upserted, so the count of what an agent holds does not grow with what it has done. See
knowledge/domain/wallet.md.
"""

from __future__ import annotations

from orexis_progression.ontology import beliefs_graph
from orexis_progression.store import bindings

from .terms import BALANCE, HAS_ENDOWMENT

_XSD = "http://www.w3.org/2001/XMLSchema#"

#  What is left, and what was brought — in that order. A wallet nobody has spent from holds no
#  balance row, and reads as the endowment: absence is the opening figure rather than zero,
#  which is the difference between a new agent and a broke one.
#  BOTH ARE THE AGENT'S OWN, so both are read from its own graph and the graph is named. An
#  unqualified pattern reads PUBLIC knowledge, and a wallet is the one thing in this society
#  that must never arrive that way.
_BALANCE_Q = """
SELECT ?balance ?endowment WHERE { GRAPH <%s> {
  OPTIONAL { <%s> <%s> ?balance }
  OPTIONAL { <%s> <%s> ?endowment }
} }"""


def balance_of(agent) -> float:
    """What this agent has left. The endowment until it has won anything."""
    graph = beliefs_graph(agent.id)
    rows = bindings(agent.beliefs.query(
        _BALANCE_Q % (graph, agent.me.uri, BALANCE, agent.me.uri, HAS_ENDOWMENT)))
    if not rows:
        return 0.0
    row = rows[0]
    if row.get("balance") is not None:
        return float(row["balance"])
    return float(row["endowment"]) if row.get("endowment") is not None else 0.0


def debit(agent, amount: float) -> float:
    """Spend, and write down what is left. Returns the new balance.

    Upserted rather than appended: an agent's belief base holds a fixed number of nodes however
    long it runs, and a wallet that grew a row per purchase would be the appending this project
    watches `belief_triples` to catch.
    """
    left = round(balance_of(agent) - float(amount), 6)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{agent.me.uri}> <{BALANCE}> ?was }} }}
INSERT {{ GRAPH <{beliefs_graph(agent.id)}> {{
  <{agent.me.uri}> <{BALANCE}> "{left}"^^<{_XSD}decimal> }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{beliefs_graph(agent.id)}> {{
  <{agent.me.uri}> <{BALANCE}> ?was }} }} }}""")
    return left
