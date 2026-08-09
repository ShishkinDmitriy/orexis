"""The entailments both engines must agree on, computed once at boot.

Two engines read this society's graphs and they used to disagree about what it says. `pyshacl`
validates with `inference="rdfs"`, so a shape's SPARQL sees `onewire:DataPinRole a mc:OutputRole`
— entailed through two `rdfs:subClassOf` steps and asserted nowhere. `pyoxigraph` infers nothing,
so the runtime sees only what the files literally say. **A world could therefore validate against
a relationship the code would never observe.**

The half of that story usually told is "the runtime does no inference", and it is not quite
right. The runtime infers *by hand*: six queries carried `rdfs:subClassOf*` property paths to
compensate, in `runtime.py` and in three capabilities' `rules.ru`. Twenty-five subclass axioms
were declared and only those six sites read them, so an axiom's meaning depended on whether
whoever wrote the query happened to remember. That is the failure this module removes — not
absent inference, but inference that had to be remembered.

**What is materialised is deliberately narrow.** Full RDFS entailment would assert that every
resource is an `rdfs:Resource` and every property a `rdf:Property`, which is true, useless, and
would multiply the triple count an agent reports as flat (see knowledge/domain/agent-metrics.md).
What is computed here is exactly what the code and the shapes actually ask: subclass and
subproperty transitivity, and the type and property entailments that follow from them.

**It cannot go stale.** `refresh_public` replaces the ontology and world graphs from the ratified
files on every start and then re-runs this, so the closure is a function of the files rather than
an accumulation. Nothing here is written to a graph an agent owns.

**Where SHACL did not need it, and why that misleads.** `sh:targetClass` and `sh:class` match
subclasses *by specification* — a SHACL instance of a class is an instance of any subclass — so
dropping inference from validation leaves those working and hides the problem. What breaks is
`rdf:type` inside `sh:sparql`, which is ordinary SPARQL and does no such thing. Measured: seven
shape tests fail with inference off, every one of them a `?role a mc:…Role` test inside a SPARQL
constraint. See knowledge/decisions/one-graph-both-engines-read.md.
"""

from __future__ import annotations

import logging

from .ontology import ONTOLOGY_GRAPH, WORLD_GRAPH

log = logging.getLogger("inference")

# One pass, not a fixpoint loop: `+` is already the transitive closure, so asking for it directly
# computes in one update what iterating single steps would take several rounds to reach.
#
# The `FILTER(?a != ?b)` guards are not pedantry. A cycle in the class hierarchy — legal RDF, and
# the kind of thing a generated vocabulary produces — makes every class in it a subclass of
# itself, and `?x a ?x` after that. Neither is false, both are noise.
_CLOSURE = (
    # 1. subClassOf and subPropertyOf are transitive. Done first, so the entailments below can
    #    read a single step and still see the whole chain.
    f"""INSERT {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?a rdfs:subClassOf ?b }} }}
        WHERE  {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?a rdfs:subClassOf+ ?b }} FILTER(?a != ?b) }}""",
    f"""INSERT {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?a rdfs:subPropertyOf ?b }} }}
        WHERE  {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?a rdfs:subPropertyOf+ ?b }} FILTER(?a != ?b) }}""",

    # 2. What a T-Box individual is. This is the one the shapes were quietly relying on:
    #    `onewire:DataPinRole a mc:BidirectionalRole` becomes `a mc:OutputRole` and `a mc:PinRole`,
    #    which is what the rule keeping a driven line off an input-only pin asks about.
    f"""INSERT {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?x a ?super }} }}
        WHERE  {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?x a ?class . ?class rdfs:subClassOf ?super }}
                  FILTER(?class != ?super) }}""",

    # 3. What a WORLD instance is, given classes the ontology declares. Two graphs, because an
    #    instance is the world's and the class hierarchy is the vocabulary's — which is exactly
    #    the join no single-graph query could make and every reader had to write out by hand.
    f"""INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?x a ?super }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}>    {{ ?x a ?class }}
                  GRAPH <{ONTOLOGY_GRAPH}> {{ ?class rdfs:subClassOf ?super }}
                  FILTER(?class != ?super) }}""",

    # 4. And what a world statement implies under a subproperty. There are no `rdfs:subPropertyOf`
    #    axioms today — the simulated-device work removed the last one, `ag:models` under
    #    `ag:polls`, which is the very fault that opened issue #27. This is here so that
    #    reintroducing one is a vocabulary edit and not a debugging session.
    f"""INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ?x ?super ?y }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}>    {{ ?x ?p ?y }}
                  GRAPH <{ONTOLOGY_GRAPH}> {{ ?p rdfs:subPropertyOf ?super }}
                  FILTER(?p != ?super) }}""",
)


def materialise(store) -> None:
    """Assert what the vocabulary entails, so that every reader sees one graph.

    Run from `genesis.refresh_public` after the files are loaded and BEFORE each package's
    `rules.ru`, so a derivation rule may ask `?type a ag:Sensor` and mean it — rather than
    spelling out a property path and hoping the next rule's author remembers to.
    """
    before = len(store)
    for update in _CLOSURE:
        store.update(update)
    log.debug("entailments materialised: %d triples -> %d", before, len(store))
