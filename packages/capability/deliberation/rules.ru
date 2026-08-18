# Derivation: who deliberates — from a stake AND a lever, the same premise that grants keeping.
#
# The same premise DELIBERATELY, not coincidentally: deciding what to do about a gap and
# remembering what was decided are meaningful under exactly the same conditions — something to
# advance for, and some way to act on it. An agent with either half missing has nothing to
# decide; world/sensing's agent records, the supplier hosts, and neither arises here.
#
# They stay two capabilities despite the shared premise because they are different ABILITIES
# with different replaceable parts: how commitments are kept could change without changing how
# decisions are reached, and — the case this family exists for — the other way round. One rule
# each, in the package that owns the conclusion.
#
# deliberation:Consulting is deliberately ABSENT, exactly as desire's and review's are. What
# would SELECT between reflex and a model once both exist is an open seam — the rule is the
# last piece to add, not the first.

PREFIX deliberation: <http://example.org/agora/deliberation#>
PREFIX sensing: <http://example.org/agora/sensing#>
PREFIX actuation: <http://example.org/agora/actuation#>
PREFIX market: <http://example.org/agora/market#>
PREFIX ag:   <http://example.org/agora#>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>

INSERT { GRAPH $derived {
    ?agent ag:hasCapability deliberation:Reflex } }
$given
WHERE  {
    ?agent a ag:Agent ; ag:actsFor ?subject .
    ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?condition .
    ?condition ssn:forProperty ?property ;
               schema:minValue ?min ;
               schema:maxValue ?max .
    { ?agent market:bidsIn ?market }
    UNION
    { ?agent actuation:hasActuator ?actuator }
    UNION
    { ?agent sensing:polls ?sensor .
      ?sensor sensing:senseMode sensing:ScheduledProcedure }
}
 ;

# Derivation: who PLANS — the dealer premise: levers that compose.
#
# Depth-2 deliberation is meaningful for exactly one shape of agent: one whose levers chain —
# a lever whose effect makes another of its levers meaningful. The dealer is that shape, at
# the level of GIVEN facts: it acts for a source it offers (its shop's vessel is its stake),
# and a pipe fills that vessel from a source someone else offers (so there is an upstream to
# acquire in). Acquiring upstream is what makes offering downstream possible — the refill-
# then-sell dependency the planning record calls the first honest customer.
#
# Stated from given facts only, like every rule: market:offeredBy arrives entailed from each
# domain's word (water's suppliedBy), the pipe is the same drawsFrom/actuates pair the
# participation rule reads, and the matching statements are the two consents. bidsIn and
# hosts are NOT premises — they are other rules' conclusions, and a derivation reads facts,
# never conclusions, so the dealer premise recomputes what it needs of them.
#
# The reflex's premise is a subset of this one, so a planner always also derives Reflex —
# deliberately: they are both true abilities, the planner subsumes the reflex's answers, and
# `provider` hands actors the planner (pinned by a test, not by the accident of sort order).

INSERT { GRAPH $derived {
    ?agent ag:hasCapability deliberation:Planning } }
$given
WHERE  {
    ?agent a ag:Agent ; ag:actsFor ?vessel .
    ?vessel market:offeredBy ?agent .
    ?agent market:matchesBy ?selling .
    ?selling a market:BidMatchingCapability .
    ?pipe actuation:drawsFrom ?upstream ;
          actuation:actuates ?vessel .
    ?upstream market:offeredBy ?owner .
    ?owner market:matchesBy ?buying .
    ?buying a market:BidMatchingCapability .
    FILTER(?agent != ?owner)
}
