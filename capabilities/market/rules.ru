# Derivation: market capabilities follow from the topology of the venue.
#
# An agent plumbed into a market is a bidder there; the one that owns the venue hosts it.
# Neither is a declaration — both are consequences of how the world is wired.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT { GRAPH <http://example.org/agora/graph/world> { ?agent ag:hasCapability ag:Bidding } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> { ?agent ag:bidsIn ?market . ?market a ?type }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:Market }
} ;

INSERT { GRAPH <http://example.org/agora/graph/world> { ?agent ag:hasCapability ag:Hosting } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> { ?agent ag:hosts ?market . ?market a ?type }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:Market }
}
