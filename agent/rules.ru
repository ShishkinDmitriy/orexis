# Derivation: which pick record belongs to which agent — typed by what it IS, a
# record (#312): the desire modality projects it by name, so no modality typing remains.
#
# This used to be written out by hand, once per agent, in every world — four lines of
# `<…/graph/beliefs/fern> a orexis:BeliefsGraph ; orexis:beliefsOf orexis:fern_agent .` that had to be kept
# in step with the roster above them. A second list is a second thing to drift, and this one
# drifted silently: nothing failed if an agent was added and its line was not.
#
# It is a FUNCTION of the roster. The graph's IRI is built from the agent's own localId, exactly
# as `ontology.beliefs_graph()` builds it — which is the one instance identifier a process is
# allowed to name, so constructing from it here is the same permission, spelled in SPARQL.
#
# `$given` and `$derived` are substituted by the loader (see genesis.substitute): a rule says
# what it concludes and never names a graph.

PREFIX orexis:   <http://example.org/orexis#>

INSERT { GRAPH $derived {
    ?graph a orexis:PickRecordGraph ; orexis:beliefsOf ?agent } }
$given
WHERE  {
    ?agent a orexis:Agent ; orexis:localId ?id .
    BIND(IRI(CONCAT("http://example.org/orexis/graph/beliefs/", ?id)) AS ?graph)
}
