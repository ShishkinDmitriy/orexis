"""`extract`: what the agent comes to believe of one statement — what every extraction it holds
concludes of it, one belief graph derived from it.

**AS SENSING REVISES A PERCEPT ALONE, SPEECH EXTRACTS FROM A STATEMENT ALONE.** An extraction
(`speech:Extraction`) is a domain's `sh:construct`, shipped in its rules graph; each is asked over the
one statement and the world's documents beside it, and over nothing else the agent holds, so it reads
what was said and never what was believed before — a transition, which reads the agent's own state
beside its arrival, would carry what an earlier statement said into the belief made of a later one. What
every extraction constructs is written into one belief graph of the agent's own, derived from the
statement (`prov:wasDerivedFrom`), arrived `orexis:Derived`, holding over the statement's period: so a
round believed holds while the round said does, and goes when it is said again, as a revision goes with
its source (`forget_graph`). A statement nothing extracts from leaves no belief at all.

**THE LANGUAGE IS A COINCIDENCE.** The market says the triples its agents believe, so its extraction
restates what was said. A society speaking another language — English an LLM reads — would swap what
runs here, and no reader of the mind would learn of it.

**AN EXTRACTION THAT WILL NOT RUN EXTRACTS NOTHING, LOUDLY.** A package's bug must not take an agent
down: said in the log, naming the rule, and the rest still run.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.hash_named_graph import hash_named_graph
from agent.ontology import BELIEF, OREXIS, local_of
from agent.store import Raw, add_quads, catalogue_of, construct, entry, forget_graph, graphs_of, rows, update

from .ontology import believed_graph

log = logging.getLogger("speech")

_RULES_GRAPH = "http://www.w3.org/ns/shacl#RulesGraph"

#  EVERY ACTIVE EXTRACTION, with its text, over the rules graphs.
_EXTRACTIONS_Q = """
SELECT ?rule ?text WHERE { ?rule a speech:Extraction ; sh:construct ?text .
                           FILTER NOT EXISTS { ?rule sh:deactivated true } } ORDER BY ?rule"""

#  THE STATEMENT'S ROW: whose it is and when it holds.
_ROW_Q = """
SELECT ?owner ?start ?end WHERE { GRAPH $cat { OPTIONAL { $g orexis:beliefsOf ?owner }
  OPTIONAL { $g dcterms:temporal ?p . OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }
LIMIT 1"""


def extract(store: ox.Store, statement: str) -> list[str]:
    """Write what every extraction concludes of `statement` into the belief graph derived from it,
    replacing what was extracted of it before. The belief graph written, or none where nothing was."""
    target = believed_graph(statement)
    forget_graph(store, target)
    cat = catalogue_of(store)
    if cat is None:
        return []
    reads = [statement, *graphs_of(store, BELIEF, common=True)]
    found: list = []
    for r in rows(store, _EXTRACTIONS_Q, graphs_of(store, _RULES_GRAPH)):
        try:
            found += construct(store, r["text"], reads)
        except Exception as exc:                                    # noqa: BLE001
            log.error("%s: an extraction would not run, so it extracts nothing: %s", local_of(r["rule"]), exc)
    if not found:
        return []
    row = next(iter(rows(store, _ROW_Q, (), cat=Raw(f"<{cat}>"), g=Raw(f"<{statement}>"))), {})
    add_quads(store, (ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(target)) for t in found))
    update(store, f"""INSERT DATA {{ {entry(store, target, BELIEF, OREXIS + "Derived", row.get("owner"), row.get("start"), row.get("end"))}
  GRAPH <{cat}> {{ <{target}> prov:wasDerivedFrom <{statement}> }} }}""")
    hash_named_graph(store, target)
    return [target]
