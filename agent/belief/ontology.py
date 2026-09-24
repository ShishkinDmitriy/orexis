"""The belief package's own words, and the name it spells for eyes.

THE RULE VOCABULARY IS SHACL 1.2 INFERENCE RULES', ADOPTED AS IT STANDS: the graph in the role
of a rules graph, the rule set a package ships, the SPARQL rule with its construct, layer,
order, deactivation and run-once. Every one of those is spelled by the store's dictionary in a
text, and named here only for the two readers in Python. What is ours is one graph kind: the
inference graph of one source, which the draft names as a role and not a class
(`ontology.ttl` beside this file).

THE NAME IS FOR EYES. A source's revision graph is spelled from the source's own name; every
reader asks the catalogue by class and by provenance, and renaming it here would change
nothing a reader sees.
"""

from __future__ import annotations

BELIEF = "http://example.org/orexis/belief#"
SH = "http://www.w3.org/ns/shacl#"

#  THE DRAFT'S OWN: the graph in the role of a rules graph, which `revise` reads by kind.
RULES_GRAPH = SH + "RulesGraph"

#  OURS: the graph of revisions — one per source — and whether its rules settled over it.
REVISION_GRAPH = BELIEF + "RevisionGraph"
SETTLED = BELIEF + "settled"

PROV = "http://www.w3.org/ns/prov#"
DERIVED_FROM = PROV + "wasDerivedFrom"


def revision_graph(source: str) -> str:
    """Where the revisions of `source` — what the rules conclude of it — are kept."""
    return source + "/revisions"
