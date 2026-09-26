"""An action's implementation: the operations taking a step does, read off the action's row.

An action's `execution:implementation` holds `execution:operation`s, each of a kind execution knows — an
`execution:Command` to a device (an `sh:select`), an `execution:Saying` to a peer (an
`sh:construct`), an `execution:Fictive` writing the step's own effect — grouped by `sh:order`, an
absent order being 0 as SHACL says. A noun: the one read `operations` answers, which `command`,
`says` and the executor each ask.
"""

from __future__ import annotations

from typing import NamedTuple

from agent.ontology import ACTION
from agent.store import graphs_of, rows

from .ontology import EXECUTION

COMMAND = EXECUTION + "Command"
SAYING = EXECUTION + "Saying"
FICTIVE = EXECUTION + "Fictive"

_OPERATIONS_Q = """
SELECT ?kind ?order ?text WHERE {
  $action execution:implementation/execution:operation ?op .
  ?op a ?kind . VALUES ?kind { execution:Command execution:Saying execution:Fictive }
  OPTIONAL { ?op sh:order ?o } OPTIONAL { ?op sh:select ?select } OPTIONAL { ?op sh:construct ?construct }
  BIND(COALESCE(?o, 0) AS ?order) BIND(COALESCE(?select, ?construct) AS ?text) }
ORDER BY ?order ?kind ?text"""


class Operation(NamedTuple):
    kind: str
    order: float
    text: str | None


def operations(store, action: str) -> list[Operation]:
    """Every operation the action's implementation holds, in order — none for an action stating
    no implementation, whose steps are said in the log and nothing else."""
    return [Operation(r["kind"], float(r["order"]), r.get("text"))
            for r in rows(store, _OPERATIONS_Q, graphs_of(store, ACTION), action=action)]
