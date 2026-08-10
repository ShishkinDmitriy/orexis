# Derivation: how a host matches, from what it says it matches by.
#
# The premise is the HOST'S OWN STATEMENT. An auction is a process, not a standing thing, and
# the one who convenes it defines its terms — so how bids are matched is a fact about the host
# rather than about the venue. Two hosts of one market could in principle run different auctions;
# a market that stated the matching for them could not express that, and would also be claiming
# something no participant asked it to hold.
#
# `ag:matchesBy` is stated; the capability is derived from it. That distinction is the whole
# reason this is derived and not declared: `world.ttl` may not contain `ag:hasCapability`,
# and it does not — it contains what the host does, and the ability follows.
#
# Guarded on ag:hosts as well, so a would-be host that says how it matches but owns no venue
# derives nothing. Stating how you would run an auction you cannot convene is an authoring slip,
# and the shape says so; this derivation simply does not act on it.
#
# A member declared but unimplemented is deliberately reachable by this same derivation.
# A world that states one derives the capability, and the agent then logs at startup that
# nothing provides it — which is the honest failure and exactly what `ag:Polling` and
# `ag:Consulting` already do. See knowledge/domain/bid-matching.md.

PREFIX ag:   <http://example.org/agora#>

INSERT { GRAPH $derived {
    ?agent ag:hasCapability ?matching } }
$given
WHERE  {
    ?agent ag:hosts ?market ; ag:matchesBy ?matching .
    ?market a ag:Market .
    ?matching a ag:BidMatchingCapability .
}
