# Derivation: market capabilities follow from the topology of the venue.
#
# An agent plumbed into a market is a bidder there; the one that owns the venue hosts it.
# Neither is a declaration — both are consequences of how the world is wired.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  `USING` merges what is GIVEN: the sovereign's world, and what the vocabulary entails of it.
#  Never another rule's output — a derivation reads facts, not conclusions, so no rule can
#  quietly depend on the order the packages happen to load in.
INSERT { GRAPH <http://example.org/agora/graph/world/derived> {
    ?agent ag:hasCapability ag:Bidding } }
USING <http://example.org/agora/graph/ontology>
USING <http://example.org/agora/graph/ontology/entailed>
USING <http://example.org/agora/graph/world>
USING <http://example.org/agora/graph/world/entailed>
WHERE  { ?agent ag:bidsIn ?market . ?market a ag:Market } ;

INSERT { GRAPH <http://example.org/agora/graph/world/derived> {
    ?agent ag:hasCapability ag:Hosting } }
USING <http://example.org/agora/graph/ontology>
USING <http://example.org/agora/graph/ontology/entailed>
USING <http://example.org/agora/graph/world>
USING <http://example.org/agora/graph/world/entailed>
WHERE  { ?agent ag:hosts ?market . ?market a ag:Market }
