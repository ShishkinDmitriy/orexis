# Derivation: which rule a host runs, from the rule it says it runs.
#
# The premise is the HOST'S OWN STATEMENT. An auction is a process, not a standing thing, and
# the one who convenes it defines its terms — so the format is a fact about the host rather
# than about the venue. Two hosts of one market could in principle run different auctions; a
# market that stated the format for them could not express that, and would also be claiming
# something no participant asked it to hold.
#
# `ag:matchesBy` is stated; the capability is derived from it. That distinction is the whole
# reason this is a rule and not a declaration: `world.ttl` may not contain `ag:hasCapability`,
# and it does not — it contains what the host does, and the ability follows.
#
# Guarded on ag:hosts as well, so a would-be host that states a rule but owns no venue derives
# nothing. Stating how you would run an auction you cannot convene is an authoring slip, and
# the shape says so; this rule simply does not act on it.
#
# ag:UniformPrice is deliberately reachable by this same rule and deliberately unimplemented.
# A world that states it derives the capability, and the agent then logs at startup that
# nothing provides it — which is the honest failure and exactly what `ag:Polling` and
# `ag:Consulting` already do. See knowledge/decisions/an-auction-format-is-a-capability.md.

PREFIX ag:   <http://example.org/agora#>

INSERT { GRAPH $derived {
    ?agent ag:hasCapability ?format } }
$given
WHERE  {
    ?agent ag:hosts ?market ; ag:matchesBy ?format .
    ?market a ag:Market .
    ?format a ag:MatchingCapability .
}
