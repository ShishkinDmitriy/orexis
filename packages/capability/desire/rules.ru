# Derivation: who holds a desire, and what that desire is.
#
# TWO rules and they answer different questions. The first grants the capability; the second
# computes the regions. They are separate because the premise of a grant is a fact about the
# AGENT ("it acts for something with stated needs") and the content of a region is arithmetic
# over conditions — and an agent that is granted the capability but whose ranges contradict each
# other must end up with the capability and no region, so that its own shapes can say so.
#
# THE PREMISE IS A STAKE. AGENTS.md: each capability is granted by whatever fact makes it
# meaningful, and that fact is its own. Sensing's is equipment, review's is latitude, and
# this one's is having something to advance for — `ag:actsFor`, plus a subject that states what
# it needs. An agent wired to a sensor and to nothing else records; it wants nothing, and
# world/sensing says exactly that in a comment already: "with nothing to advance for it, this
# agent holds no stake — it records." That sentence is now a rule.
#
# desire:Consulting is deliberately ABSENT, exactly as the review capability's is. The vocabulary
# declares it because the judgement is the replaceable part and the T-Box should say so; nothing
# implements it, and granting a capability no module provides would only produce a warning at
# startup. What would SELECT between the two once both exist is an open seam.

PREFIX desire: <http://example.org/agora/desire#>
PREFIX market: <http://example.org/agora/market#>
PREFIX actuation: <http://example.org/agora/actuation#>
PREFIX sensing: <http://example.org/agora/sensing#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX ag:   <http://example.org/agora#>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>

#  1. The grant. Something to advance for, and a subject that says what it needs.
#
#  Both halves are required and neither is enough. An agent acting for a subject that states no
#  range has nothing to deduce from, and granting it the capability would produce a module with
#  no region and an agent that fails its own validation at boot for a reason nobody authored.
INSERT { GRAPH $derived {
    ?agent ag:hasCapability desire:Deducing } }
$given
WHERE  {
    ?agent a ag:Agent ; ag:actsFor ?subject .
    ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?condition .
    ?condition ssn:forProperty ?property ;
               schema:minValue ?min ;
               schema:maxValue ?max .
} ;

#  1b. The grant for OWING, whose premise is not a stake at all.
#
#  A lever others can demand through a venue this agent hosts — the honoured row's own premise,
#  read from the side of the agent that will be asked. Both halves again: hosting a market with
#  no actuator is issuing paper nobody can spend here, and holding an actuator while hosting
#  nothing means nobody may demand it.
#
#  It names the market's vocabulary and that is not a package reaching into another's Python:
#  a premise is a fact about the world, and the fact that makes owing meaningful happens to be
#  market-shaped. What this package may not do is import the market's code, and it does not.
#
#  AUTHORED AND ENTAILED FACTS ONLY, which is a constraint the first draft of this rule learnt
#  the hard way. Rules run ONCE, in package-directory order, so `desire/` runs before `market/`
#  and a premise resting on `market:hosts` — which the market package DERIVES — matched nothing
#  and granted nothing, silently. The same three facts are sayable without it: the agent offers
#  the source (`market:offeredBy`, entailed from the domain's own word before any rule runs), it
#  consents to a venue (`market:matchesBy`, authored — stating your matching rule is opening
#  shop), and it holds a lever drawing from that source. That is "others may demand this lever
#  through a venue of mine", in facts that exist before any package concludes anything.
#
#  Deliberately NOT joined to `desire:Deducing`. The city hosts, owes and has no stake; the
#  supplier has all three. Two premises, two grants, and an agent may compose either, both or
#  neither.
INSERT { GRAPH $derived {
    ?agent ag:hasCapability desire:Owing } }
$given
WHERE  {
    ?agent a ag:Agent ; market:matchesBy ?matching ; actuation:hasActuator ?lever .
    ?source market:offeredBy ?agent .
    ?lever actuation:drawsFrom ?source .
}
