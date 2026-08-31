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

from orexis_agent_progression.ontology import (ONTOLOGY_ENTAILED_GRAPH, ONTOLOGY_GRAPH, WORLD_ENTAILED_GRAPH,
                       WORLD_GRAPH)

log = logging.getLogger("inference")

# What this module reads: the asserted vocabulary, and whatever it has already entailed from it.
# Both, because step 3 needs the transitivity steps 1 and 2 just computed — and those landed in
# the entailed graph, not the asserted one it read them from.
_T_BOX = f"USING <{ONTOLOGY_GRAPH}>\nUSING <{ONTOLOGY_ENTAILED_GRAPH}>"

# One pass, not a fixpoint loop: `+` is already the transitive closure, so asking for it directly
# computes in one update what iterating single steps would take several rounds to reach.
#
# The `FILTER(?a != ?b)` guards are not pedantry. A cycle in the class hierarchy — legal RDF, and
# the kind of thing a generated vocabulary produces — makes every class in it a subclass of
# itself, and `?x a ?x` after that. Neither is false, both are noise.
#
# Every entailment lands in an `entailed` graph and never in the asserted one it was computed
# from. That is what makes "who put this here" answerable: the vocabulary a package wrote stays
# exactly as written, and what RDFS made of it sits beside it, distinguishable by anyone who
# cares and invisible to everyone who does not — because `store.query` merges the lot by default.
CLOSURE = (
    # 1. subClassOf and subPropertyOf are transitive. Done first, so the entailments below can
    #    read a single step and still see the whole chain.
    f"""INSERT {{ GRAPH <{ONTOLOGY_ENTAILED_GRAPH}> {{ ?a rdfs:subClassOf ?b }} }}
        {_T_BOX}
        WHERE  {{ ?a rdfs:subClassOf+ ?b FILTER(?a != ?b) }}""",
    f"""INSERT {{ GRAPH <{ONTOLOGY_ENTAILED_GRAPH}> {{ ?a rdfs:subPropertyOf ?b }} }}
        {_T_BOX}
        WHERE  {{ ?a rdfs:subPropertyOf+ ?b FILTER(?a != ?b) }}""",

    # 2. What a T-Box individual is. This is the one the shapes were quietly relying on:
    #    `onewire:DataPinRole a mc:BidirectionalRole` becomes `a mc:OutputRole` and `a mc:PinRole`,
    #    which is what the rule keeping a driven line off an input-only pin asks about.
    #
    #    `isIRI(?super)` because a superclass may now be an anonymous CLASS EXPRESSION rather than
    #    a class name — rule 5 introduced the first `rdfs:subClassOf [ a owl:Restriction … ]` into
    #    the vocabulary. `?x a _:restriction` is perfectly true and no reader can ask for it: a
    #    blank node has no name to put in a query. True and useless is the category this closure
    #    exists to leave out.
    f"""INSERT {{ GRAPH <{ONTOLOGY_ENTAILED_GRAPH}> {{ ?x a ?super }} }}
        {_T_BOX}
        WHERE  {{ ?x a ?class . ?class rdfs:subClassOf ?super
                  FILTER(?class != ?super && isIRI(?super)) }}""",

    # 3. What a WORLD instance is, given classes the ontology declares. The join spans the world
    #    and the vocabulary — and the world side is NAMED rather than merged, which is the whole
    #    correctness of this rule.
    #
    #    `USING` merges its graphs into one default graph, and a merged pattern cannot say which
    #    graph it matched. So reading the vocabulary and the world together made this rule fire on
    #    T-Box individuals as well — and since the graph catalog is itself asserted in the
    #    vocabulary, `<…/graph/world> a orexis:Graph` was entailed twice, once by rule 2 into
    #    `ontology/entailed` and again by this one into `world/entailed`. Semantically harmless,
    #    and it inflated a triple count that agent-metrics reports as flat while leaving "which
    #    graph holds this entailment" without a single answer.
    #
    #    `USING NAMED` keeps the world reachable as itself, so the pattern can insist an instance
    #    came from the world while still reading the vocabulary merged.
    f"""INSERT {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?x a ?super }} }}
        {_T_BOX}
        USING NAMED <{WORLD_GRAPH}>
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?x a ?class }}
                  ?class rdfs:subClassOf ?super
                  FILTER(?class != ?super && isIRI(?super)) }}""",

    # 4. And what a world statement implies under a subproperty. There are no `rdfs:subPropertyOf`
    #    axioms today, again: the simulated-device work removed `orexis:models` under
    #    `sensing:polls` — the very fault that opened issue #27 — then #79 added `mc:carries`
    #    under `sosa:hosts`, and dropping that term for the standard one removed it again. Both
    #    removals were right and neither touched this rule, which is the point: it is here so
    #    that reintroducing one is a vocabulary edit and not a debugging session, and it has now
    #    survived a full cycle of one appearing and going away.
    f"""INSERT {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?x ?super ?y }} }}
        {_T_BOX}
        USING NAMED <{WORLD_GRAPH}>
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?x ?p ?y }}
                  ?p rdfs:subPropertyOf ?super FILTER(?p != ?super) }}""",

    # 5. And what a world instance HAS, given a value its class fixes for every member. The one
    #    OWL construct here, and it earns its place: `owl:hasValue` is how a vocabulary says "every
    #    instance of this class has this property value" — a datasheet fact, stated once on the
    #    part and reaching each device built from it.
    #
    #    Without it a class-level statement is PUNNING: `dht11:Dht11 ssn-system:hasSystemCapability
    #    …` is legal RDF and entails nothing about instances, so the fact had to be written a
    #    second time onto each sensor in the world — which is #59, and which a test had to guard
    #    because nothing else could.
    #
    #    Rule 1 has already run, so a restriction on a SUPERCLASS is reached too: `?class
    #    rdfs:subClassOf ?restriction` reads the transitive closure and not one step.
    #
    #    Deliberately just this one. `owl:someValuesFrom` says a value exists without naming it,
    #    which materialises nothing; `owl:allValuesFrom` constrains values rather than asserting
    #    them; cardinality is a shape's job here and pyshacl already does it. `hasValue` is the
    #    only OWL class expression that turns into ground triples, which is why it is the only one
    #    a materialising closure can honour at all.
    f"""INSERT {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?x ?p ?v }} }}
        {_T_BOX}
        USING NAMED <{WORLD_GRAPH}>
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?x a ?class }}
                  ?class rdfs:subClassOf ?restriction .
                  ?restriction a owl:Restriction ; owl:onProperty ?p ; owl:hasValue ?v }}""",

    # 6. What a chain of two world statements concludes, where the vocabulary declares the
    #    chain. The one consumer today is SSN's own axiom for `sosa:hosts` — a platform in a
    #    deployment that deploys a system HOSTS that system (#99) — restated in
    #    capabilities/sensing/ontology.ttl because we borrow IRIs and never import ontologies.
    #    Hosting is what a deployment produces, and asserting the conclusion beside an absent
    #    premise is the shape of debt this closure exists to retire.
    #
    #    TWO links, deliberately, the way rule 5 honours exactly one OWL construct: every chain
    #    any ontology here states is two long, an n-link walk is a different piece of machinery,
    #    and a rule that silently handled only part of a longer chain would be worse than one
    #    that visibly does not try. Both premises must be WORLD statements — a chain across the
    #    T-Box is not a fact about anyone's bench.
    f"""INSERT {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?a ?conclusion ?c }} }}
        {_T_BOX}
        USING NAMED <{WORLD_GRAPH}>
        WHERE  {{ ?conclusion owl:propertyChainAxiom ?chain .
                  ?chain rdf:first ?first ;
                         rdf:rest [ rdf:first ?second ; rdf:rest rdf:nil ] .
                  GRAPH <{WORLD_GRAPH}> {{ ?a ?first ?b . ?b ?second ?c }} }}""",
)

# Emptied before recomputing, because they are a function of the files and not an accumulation.
# `refresh_public` replaces the asserted graphs with `put_graph`, which clears as it loads; these
# are written by update and would otherwise keep last boot's answer beside this boot's.
ENTAILED_GRAPHS = (ONTOLOGY_ENTAILED_GRAPH, WORLD_ENTAILED_GRAPH)


def materialise(store) -> None:
    """Assert what the vocabulary entails, so that every reader sees one graph.

    Run from `genesis.refresh_public` after the files are loaded and BEFORE each package's
    `rules.ru`, so a derivation rule may ask `?type a sensing:Sensor` and mean it — rather than
    spelling out a property path and hoping the next rule's author remembers to.
    """
    before = len(store)
    for update in CLOSURE:
        store.update(update)
    log.debug("entailments materialised: %d triples -> %d", before, len(store))
