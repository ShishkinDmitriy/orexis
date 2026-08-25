"""The aim: the point an agent steers a property toward, picked inside the region it holds.

What is left of `agent/regions.py` after the region went to sensing (the-stake-is-sensings-want).
An aim is a BELIEF — private, revisable by review, checked by `ag:AimShape` against the region
the want states — and reading one is the whole of what the kernel still does with a property
of its own accord. Whose region it sits inside is sensing's to say.
"""

from __future__ import annotations

from .ontology import beliefs_graph
from .store import bindings

# My own aims — the pick inside each region, one per property I chose to steer. PRIVATE, so the
# graph is named: an unqualified pattern reads public knowledge, and an aim is exactly what must
# never arrive that way.
_AIMS_Q = """
SELECT ?property ?value WHERE {{ GRAPH <{beliefs}> {{
  <{me}> ag:aims ?aim .
  ?aim ssn:forProperty ?property ;
       schema:value ?value .
}} }}"""



def aims_of(query, agent_id: str, agent_uri: str) -> dict[str, float]:
    """One agent's aims, property -> value. Private, so the beliefs graph is named.

    Takes the id as well as the URI because the graph is named from the one and the subject from
    the other — the same two facts the module itself is handed at construction.
    """
    return {row["property"]: float(row["value"])
            for row in bindings(query(_AIMS_Q.format(
                beliefs=beliefs_graph(agent_id), me=agent_uri)))}
