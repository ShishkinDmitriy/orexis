# Derivation: how many litres is too many, per participant.
#
# ONE rule, and it exists because a check in the kernel could not fire. `agent/clearing.py` has
# always refused a trade line past a participant's ceiling, and the only production caller passed
# an empty map — so `.get()` returned None for every agent and the branch was skipped for every
# line of every trade. Its unit test passed a populated map and was green, which proved the CHECK
# and not that anything filled it. See #270.
#
# WHY THE DOMAIN DERIVES IT. What counts as too much water is a fact about plants, and
# `agent/clearing.py` must name no domain. `market:lotCapacity` solves the same problem for the
# total by being a superproperty of `water:capacityL` — the world states litres, the closure
# entails the market's word, and the kernel reads a conclusion (#148). That bridge cannot carry
# this one: the number is COMPUTED, and the subproperty closure is materialised before any rule
# runs, so a derived `water:` term would never be entailed up. So this rule writes the market's
# term directly, which is what `desire`, `intention` and `deliberation` already do.
#
# WHY THE SPAN AND NOT THE HEADROOM. The obvious reading of "root-rot headroom" is
# `(ceiling - now) x litresPerFraction` — how much more this pot can take *from where it is*.
# That number is unavailable and must stay unavailable: a host cannot see a bidder's moisture,
# and agent-centric-epistemics is that the market needs its bid and not its state. What a host
# CAN know is public and structural: the span of the survival range, in litres. No honest
# allocation ever needs more than the span, because the span is the whole distance the subject
# could legitimately be moved — bone dry to the wet cliff. A line asking for more can only
# over-water, whichever end the pot started at.
#
# So this is a looser bound than a live headroom and a sound one, and it is the bound that can
# be computed from facts the host is allowed to hold. It is the constitution's shape everywhere
# else too: control the derivative, not the value — bound the envelope, never the dose.
#
# ABSENT IS NOT ZERO. A participant whose subject states no survival range gets no triple, and
# clearing checks nothing for it. `world/sensing`'s agents are exactly this: they act for
# subjects with no survival range, and a ceiling of 0.0 would refuse every trade they are in.

PREFIX water:  <http://example.org/orexis/water#>
PREFIX market: <http://example.org/orexis/market#>
PREFIX ag:     <http://example.org/orexis#>
PREFIX ssn:    <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>

#  The span of what the subject survives, in litres.
#
#  Both premises are AUTHORED or ENTAILED, never another package's conclusion: `ag:actsFor` and
#  `water:litresPerFraction` are in the world files, and the survival range reaches the pot from
#  its species by a hasValue restriction, materialised before any rule runs. See AGENTS.md on
#  why a premise may not rest on a conclusion.
#
#  Denominated in soil moisture on purpose. `water:litresPerFraction` is litres per fraction OF
#  SOIL MOISTURE — the same denomination the whole valuation uses — so the condition is pinned to
#  that property rather than matched on whichever range happens to come back. A pot whose species
#  states an air-humidity survival range as well must not have its water ceiling computed from it.
INSERT { GRAPH $derived {
    ?agent market:allocationCeilingL ?ceiling } }
$given
WHERE  {
    ?agent a ag:Agent ; ag:actsFor ?subject .
    ?subject water:litresPerFraction ?litresPerFraction ;
             ssn-system:hasSurvivalRange/ssn-system:inCondition ?condition .
    ?condition ssn:forProperty water:SoilMoisture ;
               schema:minValue ?floor ;
               schema:maxValue ?roof .
    BIND(xsd:decimal((?roof - ?floor) * ?litresPerFraction) AS ?ceiling)
}
