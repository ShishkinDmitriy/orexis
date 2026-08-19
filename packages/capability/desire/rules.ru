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
PREFIX sensing: <http://example.org/agora/sensing#>
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

#  2. The regions themselves, one per property the subject states a need in.
#
#  `$into` names the CLASS of graph these conclusions belong in, and genesis resolves it to the
#  one graph the vocabulary types that way. A rule may not name a graph — a graph IRI is an
#  instance and rule 1 applies to it — and it may not simply use `$derived` either, because
#  these are not facts about the world's wiring: they are what this package concluded, and a
#  reader asking "what does anything here want" must be able to find them without knowing that
#  the answer happens to have been computed by a rule.
#
#  THE ARITHMETIC IS INTERSECTION, and it is the whole idea. A region is where EVERY range that
#  applies agrees: the highest floor anyone states, and the lowest ceiling. Two sources
#  contribute today.
#
#    the SUBJECT — the plant's own operating range, per pot in the world or per species through
#    the closure. This is what it needs.
#
#    its INSTRUMENTS — the operating range of anything watching it. This is what can be
#    WITNESSED, and it belongs in the same intersection rather than in a separate check: a
#    region an agent cannot see itself inside is not a region it can hold. Nothing states one
#    today, so this branch is inert and deliberately shipped anyway — the day a part's datasheet
#    range lands in a world, every agent watching through that part narrows with no edit here.
#    Issue #111's sovereign-side refusal is the other half of the same fact and stays worth
#    having: silently narrowing a badly-specified rig is not the same as refusing it.
#
#  ?property is bound from the SUBJECT's own conditions, never from an instrument's. A DHT11
#  rated 0-50 °C states a fact about the DHT11; it must not become a desire to hold a pot
#  anywhere in that band. An instrument may narrow a desire and may never create one.
#
#  The envelope is OPTIONAL and gathered the same way. A world with no survival range gets a
#  region and no envelope, and the module scales urgency by the region's own width instead.
#
#  FILTER(?low <= ?high) is what an empty intersection looks like: ranges that contradict each
#  other produce no region at all, the agent keeps the capability, and `desire:DesirerShape`
#  refuses to let it start. Silence here is deliberate — a rule cannot report, and an
#  intersection quietly rounded into a point would be the worst of the three outcomes.
INSERT { GRAPH $into(desire:RegionGraph) {
    ?agent ag:desires _:region .
    _:region a ag:Desire ;
        ssn:forProperty ?property ;
        schema:minValue ?low ;
        schema:maxValue ?high ;
        ag:toleratedMin ?floor ;
        ag:toleratedMax ?ceiling } }
$given
WHERE  {
    { SELECT ?agent ?property (MAX(?min) AS ?low) (MIN(?max) AS ?high) WHERE {
        ?agent a ag:Agent ; ag:actsFor ?subject .
        ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?need .
        ?need ssn:forProperty ?property .
        { ?subject ssn-system:hasOperatingRange ?range }
        UNION
        { ?instrument sensing:monitors ?subject ; ssn-system:hasOperatingRange ?range }
        ?range ssn-system:inCondition ?condition .
        ?condition ssn:forProperty ?property ;
                   schema:minValue ?min ;
                   schema:maxValue ?max .
      } GROUP BY ?agent ?property }
    OPTIONAL {
      SELECT ?agent ?property (MAX(?least) AS ?floor) (MIN(?most) AS ?ceiling) WHERE {
        ?agent a ag:Agent ; ag:actsFor ?subject .
        ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?need .
        ?need ssn:forProperty ?property .
        { ?subject ssn-system:hasSurvivalRange ?envelope }
        UNION
        { ?instrument sensing:monitors ?subject ; ssn-system:hasSurvivalRange ?envelope }
        ?envelope ssn-system:inCondition ?tolerated .
        ?tolerated ssn:forProperty ?property ;
                   schema:minValue ?least ;
                   schema:maxValue ?most .
      } GROUP BY ?agent ?property }
    FILTER(?low <= ?high)
}
