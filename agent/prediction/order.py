"""`order`: the properties the agent predicts, in the order their keys are predicted — a property whose
flows read another's observations after that other (#996).

**A PREDICTION MAY DEPEND ON A FORECAST OF ANY AUTHOR**, the agent's own predictions among them: the
soil's drying on the air's humidity, which the agent itself foresees. A flow's `prediction:rate` is a
select, and what it reads is in its text: every `sosa:observedProperty` it names is a key it reads at
`$at` — a received forecast, another sensor's percept holding then, or the prediction this agent wrote
for that key a moment ago. So the keys are predicted in an order the texts fix: a property is predicted
after every property its flows read, and the prediction it reads is already written when it is asked.

**A CYCLE IS REFUSED, NOT ITERATED.** Soil moving by the air and air moving by the soil is a coupled
system, and a fixpoint over two piecewise-linear corridors is a solver this package is not; no shipped
world states one, so one is a mistake in the documents and `orexis-onboard` says so before anything is
granted. A flow reading its own property — the dose reads the soil's reading it lifts — is no cycle: the
reading in hand is every flow's input.

**A TEXT THAT WILL NOT BE READ READS EVERY PROPERTY** — a variable where the property stands, a body the
parser refuses — so it is predicted last, and two such texts are a cycle: the safe side, as a footprint
the planner cannot read is (`agent/planning/footprint.py`), and said aloud rather than guessed at.
"""

from __future__ import annotations

import logging
import re

from rdflib import URIRef
from rdflib.plugins.sparql.algebra import translateQuery, traverse
from rdflib.plugins.sparql.parser import parseQuery

from agent.ontology import FLOW_GRAPH, local_of
from agent.store import PREFIXES, graphs_of, rows

from .ontology import FLOW, MOVES, PROPERTY, RATE

log = logging.getLogger("predict")

ANYTHING = None          # the set of every property: a text that cannot be read reads them all

_TOKEN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\b")
_OBSERVED = URIRef(PROPERTY)

#  EVERY FLOW AND THE PROPERTY IT MOVES, with its text, off the graphs of flows alone.
_FLOWS_Q = "SELECT ?flow ?property ?rate WHERE { ?flow a $flow ; $moves ?property ; $rate_of ?rate } ORDER BY ?flow"


class Cycle(Exception):
    """Two or more properties whose flows read each other: a system, not a chain."""


def order(store, properties=None, after=None) -> list[str]:
    """`properties` — every property some flow moves, where None — in the order their keys are
    predicted: each after every property a flow moving it reads, ties in the IRIs' order. Where
    `after` names properties, those alone and every property that depends on one, transitively: what
    an arrival of their percepts makes stale. Raises `Cycle` where the texts read each other round."""
    reads = _reads(store)
    wanted = set(reads) if properties is None else set(properties)
    depends = {p: _depends_on(p, reads, wanted) for p in wanted}
    ordered = _sorted(depends)
    if after is not None:
        stale = set(after) & wanted
        grown = True
        while grown:
            grown = False
            for p, deps in depends.items():
                if p not in stale and deps & stale:
                    stale.add(p)
                    grown = True
        ordered = [p for p in ordered if p in stale]
    return ordered


def _reads(store) -> dict[str, frozenset | None]:
    """Every property some flow moves, and the properties the flows moving it read."""
    out: dict[str, set | None] = {}
    for r in rows(store, _FLOWS_Q, graphs_of(store, FLOW_GRAPH), flow=f"<{FLOW}>", moves=f"<{MOVES}>", rate_of=f"<{RATE}>"):
        read = _observed_in(r["rate"])
        if read is ANYTHING:
            log.warning("flow %s reads a property that cannot be read off its text: predicted last", local_of(r["flow"]))
        have = out.get(r["property"], set())
        out[r["property"]] = ANYTHING if have is ANYTHING or read is ANYTHING else have | read
    return {p: (frozenset(v) if v is not None else ANYTHING) for p, v in out.items()}


def _depends_on(p: str, reads: dict, wanted: set) -> set[str]:
    read = reads.get(p, frozenset())
    if read is ANYTHING:
        return wanted - {p}
    return {q for q in read if q != p and q in wanted}


def _sorted(depends: dict[str, set[str]]) -> list[str]:
    """Kahn's order, the ready ones by IRI, and a cycle named by the properties left standing."""
    left = {p: set(deps) for p, deps in depends.items()}
    out = []
    while left:
        ready = sorted(p for p, deps in left.items() if not deps)
        if not ready:
            raise Cycle("flows read each other in a cycle over " + ", ".join(sorted(local_of(p) for p in left)))
        for p in ready:
            out.append(p)
            del left[p]
        for deps in left.values():
            deps.difference_update(ready)
    return out


def _observed_in(text: str) -> frozenset | None:
    """Every property a rate text names as a `sosa:observedProperty` — the keys it reads — or
    ANYTHING where it names one by a variable or will not parse."""
    try:
        algebra = translateQuery(parseQuery(PREFIXES + _TOKEN.sub(lambda m: "?" + m.group(1), text))).algebra
    except Exception as exc:                            # noqa: BLE001 — unreadable is a finding, not an error
        log.debug("could not parse a flow's rate for the properties it reads: %s", exc)
        return ANYTHING
    found: set = set()
    bad = [False]

    def triples(entry):
        if len(entry) % 3:
            bad[0] = True
            return
        for i in range(0, len(entry), 3):
            s, p, o = entry[i:i + 3]
            if p == _OBSERVED:
                if isinstance(o, URIRef):
                    found.add(str(o))
                else:
                    bad[0] = True

    def visit(n):
        name = getattr(n, "name", None)
        if name == "BGP":
            for triple in n["triples"]:
                triples(tuple(triple))
        elif name == "TriplesBlock":
            for entry in n["triples"]:
                triples(tuple(entry))
        elif name in ("Builtin_EXISTS", "Builtin_NOTEXISTS"):
            inner = vars(n).get("graph")
            if inner is not None:
                traverse(inner, visitPost=visit)
        return n
    traverse(algebra, visitPost=visit)
    return ANYTHING if bad[0] else frozenset(found)
