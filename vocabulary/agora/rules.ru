# Derivation: which beliefs graph belongs to which agent.
#
# This used to be written out by hand, once per agent, in every world — four lines of
# `<…/graph/beliefs/fern> a ag:BeliefsGraph ; ag:beliefsOf ag:fern_agent .` that had to be kept
# in step with the roster above them. A second list is a second thing to drift, and this one
# drifted silently: nothing failed if an agent was added and its line was not.
#
# It is a FUNCTION of the roster. The graph's IRI is built from the agent's own localId, exactly
# as `ontology.beliefs_graph()` builds it — which is the one instance identifier a process is
# allowed to name, so constructing from it here is the same permission, spelled in SPARQL.
#
# `$given` and `$derived` are substituted by the loader (see genesis.substitute): a rule says
# what it concludes and never names a graph.

PREFIX ag:   <http://example.org/agora#>

INSERT { GRAPH $derived {
    ?graph a ag:BeliefsGraph ; ag:beliefsOf ?agent } }
$given
WHERE  {
    ?agent a ag:Agent ; ag:localId ?id .
    BIND(IRI(CONCAT("http://example.org/agora/graph/beliefs/", ?id)) AS ?graph)
}
