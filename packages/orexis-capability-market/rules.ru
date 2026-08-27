# Derivation: market capabilities follow from the topology of the venue.
#
# An agent plumbed into a market is a bidder there; the one that owns the venue hosts it.
# Neither is a declaration — both are consequences of how the world is wired.

PREFIX review: <http://example.org/orexis/review#>
PREFIX sensing: <http://example.org/orexis/sensing#>
PREFIX ag:   <http://example.org/orexis#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX market: <http://example.org/orexis/market#>

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
# nothing provides it — which is the honest failure and exactly what `sensing:Polling` and
# `review:Consulting` already do. See knowledge/domain/bid-matching.md.

INSERT { GRAPH $derived {
    ?agent ag:hasCapability ?matching } }
$given
WHERE  {
    ?agent market:hosts ?market ; market:matchesBy ?matching .
    ?market a market:Market .
    ?matching a market:BidMatchingCapability .
}
 ;

# Derivation: THE MARKET ITSELF, where want meets supply (a-market-arises-where-want-meets-supply).
#
# Everything a venue states is a function of facts that exist for their own reasons, except one
# triple that is CONSENT: the owner stating market:matchesBy is opening shop. A source offered
# by someone (market:offeredBy — each domain bridges its own word; water's suppliedBy among them)
# who says how they match IS a market; the node's IRI and its topics are minted from the
# source's id, on the channel precedent — a derived instance as a function of a given string,
# so any package recomputing it lands on the same node. The topics are exactly the strings the
# hand-authored venue used to state, so nothing downstream moves: only who-put-the-fact-there
# changes.
#
# The redeem window is the one figure that travels rather than being minted: it is a POLICY and
# no id implies it, so the source states how long its good is held and the venue carries it.
# On the source and not the owner because a venue is keyed by its source — one owner offering
# two goods may hold each for a different time, and that stays sayable without a new node.
#
# OPTIONAL, and that is a correction rather than laxity. Requiring it here made the venue not
# ARISE without one, which quietly made opening shop cost two triples — and the one authored
# triple being `market:matchesBy` is a claim this project makes on purpose and has a test for
# (a-market-arises-where-want-meets-supply). So consent still opens the shop, the venue is
# derived either way, and a venue with no window fails its shape LOUDLY at validation instead of
# vanishing from a world that thought it had a market. A world may still author a venue by hand where the wiring implies none; this adds,
# never forbids.
INSERT { GRAPH $derived {
    ?market a market:Market ;
        ag:localId ?marketId ;
        market:marketFor ?source ;
        market:offerTopic ?offer ; market:bidTopic ?bid ;
        market:claimTopic ?claim ; market:redeemTopic ?redeem ;
        market:redeemWindowS ?window .
    ?owner market:hosts ?market ;
           ag:hasCapability market:Hosting ;
           ag:hasCapability ?matching } }
$given
WHERE  {
    ?source market:offeredBy ?owner ; ag:localId ?srcId .
    OPTIONAL { ?source market:redeemWindowS ?window }
    ?owner market:matchesBy ?matching .
    ?matching a market:BidMatchingCapability .
    BIND(IRI(CONCAT("http://example.org/orexis#market.", ENCODE_FOR_URI(?srcId))) AS ?market)
    BIND(CONCAT(?srcId, "_market") AS ?marketId)
    BIND(CONCAT("market/", ?srcId, "/offer")  AS ?offer)
    BIND(CONCAT("market/", ?srcId, "/bid")    AS ?bid)
    BIND(CONCAT("market/", ?srcId, "/claim")  AS ?claim)
    BIND(CONCAT("market/", ?srcId, "/redeem") AS ?redeem)
} ;

# Derivation: PARTICIPATION — plumbing implies it, and the world stops naming buyers.
#
# The premises are the Acquire walk's own (#189), at the level of GIVEN facts: an agent acting
# for a subject that states a need in the denominated property, whose pot a pipe from THIS
# source reaches. The pipe is the venue-tie — drawsFrom names the source, actuates names the
# pot — so a second source's market never claims another's buyers. actuation: terms in a
# market rule, honestly, as sensing's rules name mqtt: the plumbing is the premise and there
# is no neutral word for a pipe. The market node is recomputed, not read: a derivation reads
# facts, never conclusions, so the same BINDs land on the same minted IRI.
#
# The valuation is tied through the GOOD (#198): what this source vends (entailed from its
# class — 'the lot states its good') must be what the valuation converts, or the join
# cross-multiplies the moment a second denomination exists. Without it the city's refill
# venue would claim the plants (their pots state a need in a property SOME valuation is
# about) and the barrel's venue would claim the dealer. With it, each side of one pipe
# network buys in its own market: the stake's property and the good's valuation must be the
# SAME sentence, not two facts that each happen to be true.
INSERT { GRAPH $derived {
    ?buyer market:bidsIn ?market ;
           ag:hasCapability market:Bidding } }
$given
WHERE  {
    ?source market:offeredBy ?owner ; ag:localId ?srcId .
    ?owner market:matchesBy ?matching .
    ?matching a market:BidMatchingCapability .
    ?source market:supplies ?good .
    ?valve <http://example.org/orexis/actuation#drawsFrom> ?source ;
           <http://example.org/orexis/actuation#actuates> ?pot .
    ?buyer ag:actsFor ?pot .
    ?pot <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?range .
    ?range <http://www.w3.org/ns/ssn/systems/inCondition> ?cond .
    ?cond <http://www.w3.org/ns/ssn/forProperty> ?prop .
    ?valuation market:ofGood ?good ; market:aboutProperty ?prop .
    FILTER(?buyer != ?owner)
    BIND(IRI(CONCAT("http://example.org/orexis#market.", ENCODE_FOR_URI(?srcId))) AS ?market)
}
