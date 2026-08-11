# Derivation: market capabilities follow from the topology of the venue.
#
# An agent plumbed into a market is a bidder there; the one that owns the venue hosts it.
# Neither is a declaration — both are consequences of how the world is wired.

PREFIX review: <http://example.org/agora/review#>
PREFIX perception: <http://example.org/agora/perception#>
PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX market: <http://example.org/agora/market#>

#  `$given` becomes the `USING` clauses naming every public graph, and `$derived` the graph
#  conclusions land in — substituted by the loader, because a rule should say what it concludes
#  and not know where anything is kept. A graph IRI is an instance, and a capability author who
#  had to type four of them correctly per rule was being asked to maintain a registry.
#
#  What it merges is what is GIVEN: the sovereign's world, and what the vocabulary entails of
#  it. Never another rule's output — a derivation reads facts, not conclusions, so no rule can
#  quietly depend on the order the packages happen to load in.
INSERT { GRAPH $derived {
    ?agent ag:hasCapability market:Bidding } }
$given
WHERE  { ?agent market:bidsIn ?market . ?market a market:Market } ;

INSERT { GRAPH $derived {
    ?agent ag:hasCapability market:Hosting } }
$given
WHERE  { ?agent market:hosts ?market . ?market a market:Market } ;

# Derivation: how a host matches, from what it says it matches by.
#
# The premise is the HOST'S OWN STATEMENT. An auction is a process, not a standing thing, and
# the one who convenes it defines its terms — so how bids are matched is a fact about the host
# rather than about the venue. Two hosts of one market could in principle run different auctions;
# a market that stated the matching for them could not express that, and would also be claiming
# something no participant asked it to hold.
#
# `market:matchesBy` is stated; the capability is derived from it. That distinction is the whole
# reason this is derived and not declared: `world.ttl` may not contain `ag:hasCapability`,
# and it does not — it contains what the host does, and the ability follows.
#
# Guarded on market:hosts as well, so a would-be host that says how it matches but owns no venue
# derives nothing. Stating how you would run an auction you cannot convene is an authoring slip,
# and the shape says so; this derivation simply does not act on it.
#
# A member declared but unimplemented is deliberately reachable by this same derivation.
# A world that states one derives the capability, and the agent then logs at startup that
# nothing provides it — which is the honest failure and exactly what `perception:Polling` and
# `review:Consulting` already do. See knowledge/domain/bid-matching.md.

INSERT { GRAPH $derived {
    ?agent ag:hasCapability ?matching } }
$given
WHERE  {
    ?agent market:hosts ?market ; market:matchesBy ?matching .
    ?market a market:Market .
    ?matching a market:BidMatchingCapability .
}
