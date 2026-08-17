"""The sovereign's question channel — one topic pair per agent, derived in exactly one place.

`agent-centric-epistemics` has said "observe via sovereign" since the founding records, and
this is that line made mechanism: the sovereign asks the AGENT, over the bus, and the agent
answers about itself. Not a shared store resurrected — the belief base stays the agent's, in
its own volume, reachable by nothing; what exists is a question the ACL lets exactly one
principal ask, and a voluntary answer. Disclosure, not access.

The topic shape lives HERE, and both sides import it, because the broker's ACL generator and
the agent's subscription must agree or the channel silently never works — the same
convention-vs-statement trap `PLANT_ID` fell into, resolved the other way: one function, two
callers, a test that holds them together. The world does not state these topics because they
are not the society's business: no agent may speak on another's, and the only principal that
may ask is minted by onboarding and never mounted into any agent container.

Read-only BY CONSTRUCTION, not by discipline: the responder runs `store.query`, and
pyoxigraph's query API structurally cannot execute an update — an UPDATE arrives, raises, and
is answered with the error. There is no code path from this channel to a write.
"""

SOVEREIGN = "sovereign"  # the principal's name, per world — the broker is per world already


def query_topic(agent_id: str) -> str:
    """Where the sovereign asks this agent. Writable by the sovereign principal alone."""
    return f"agents/{agent_id}/sovereign/query"


def result_topic(agent_id: str) -> str:
    """Where this agent answers. Writable by the agent alone; read by the sovereign alone."""
    return f"agents/{agent_id}/sovereign/result"
