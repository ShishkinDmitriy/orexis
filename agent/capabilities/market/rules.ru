# Derivation: market capabilities follow from the topology of the venue.
#
# An agent plumbed into a market is a bidder there; the one that owns the venue hosts it.
# Neither is a declaration — both are consequences of how the world is wired.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  `$given` becomes the `USING` clauses naming every public graph, and `$derived` the graph
#  conclusions land in — substituted by the loader, because a rule should say what it concludes
#  and not know where anything is kept. A graph IRI is an instance, and a capability author who
#  had to type four of them correctly per rule was being asked to maintain a registry.
#
#  What it merges is what is GIVEN: the sovereign's world, and what the vocabulary entails of
#  it. Never another rule's output — a derivation reads facts, not conclusions, so no rule can
#  quietly depend on the order the packages happen to load in.
INSERT { GRAPH $derived {
    ?agent ag:hasCapability ag:Bidding } }
$given
WHERE  { ?agent ag:bidsIn ?market . ?market a ag:Market } ;

INSERT { GRAPH $derived {
    ?agent ag:hasCapability ag:Hosting } }
$given
WHERE  { ?agent ag:hosts ?market . ?market a ag:Market }
