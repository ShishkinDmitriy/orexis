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
#  The bounds node is NAMED, not blank (step 2 of the-mind-is-six-graphs): a blank node is a
#  thing nothing can reference, and an intention must be able to say which goal it serves.
#  Minted as a function of the agent and the property, on the channel precedent — a derived
#  instance computed from given strings, so any package recomputing it lands on the same node
#  without reading another rule's conclusions. And it carries WHERE IT CAME FROM: the ranges
#  it was deduced from, so the sovereign asking "why am I held to 0.45" gets the answer in
#  the graph rather than in a comment.
#  What comes out is SHACL (a-desire-is-a-shape): the room a subject's stated ranges leave
#  whoever acts for it, expressed in the one language this project already has for saying what
#  a graph should look like. Two shapes from one deduction, differing in FORCE — the operating
#  region at ag:ShouldBecome, whose violation is a GAP an agent pursues; the survival envelope
#  at sh:Warning, whose violation is the subject past tolerating — loud, and never a refusal.
#  `ag:Bounds` and `ag:boundedBy` retire, and with them a two-day argument about what to call a
#  thing that binds AND motivates: it binds at one severity and motivates at the other.
#
#  DECLARATIVE on purpose, not sh:sparql: the numbers stay ordinary triples, so urgency reads
#  them with a query on every reading instead of running a validator in the hot path. Reaching
#  the value through a reified observation needs the inverse path plus a qualified shape, which
#  is convoluted to read and was measured working before it was written.
#
#  The target is the AGENT, not the subject, and the path walks `ag:actsFor` to its readings.
#  Whose desire this is, is exactly what a target answers — two agents could act for one subject
#  and want different things of it — and an agent checking itself focuses on its own node, so a
#  subject-targeted shape would be invisible at precisely the moment it matters.
#
#  The severity sits on the PROPERTY shape rather than the node shape, because that is the one
#  that produces the result — put it above and every unmet desire reports as a Violation, which
#  would refuse to boot any agent whose pot is dry.
INSERT { GRAPH $into(ag:BoundsGraph) {
    ?agent ag:holds ?bounds , ?envelope .
    ?bounds a sh:NodeShape ;
        sh:targetNode ?agent ;
        ssn:forProperty ?property ;
        prov:wasDerivedFrom ?subject ;
        sh:property [
            sh:severity ag:ShouldBecome ;
            sh:path ( ag:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            sh:qualifiedMinCount 1 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:property [ sh:path sosa:hasSimpleResult ;
                              sh:minInclusive ?low ; sh:maxInclusive ?high ] ] ;
            sh:message "a reading sits outside the region this agent holds for that property — a gap, which is what an agent is for" ] .
    ?envelope a sh:NodeShape ;
        sh:targetNode ?agent ;
        ssn:forProperty ?property ;
        prov:wasDerivedFrom ?subject ;
        sh:property [
            #  A WARNING and not a violation, which is the difference between "this world is
            #  illegitimate" and "this plant is dying". Refusing here would stop an agent
            #  booting exactly when its subject most needs it — and the envelope's real work
            #  is scaling urgency, which happens whether or not anything is validated.
            sh:severity sh:Warning ;
            sh:path ( ag:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            #  NO observation of this property may sit outside the envelope — where the region
            #  above demands that one exist INSIDE it. The asymmetry is the point and it is
            #  about evidence: not knowing is a gap an agent closes by looking, so an
            #  unmeasured property fails the region honestly; but silence is not evidence that
            #  a subject is past tolerating, and a shape that said so would have every agent
            #  reporting catastrophe at birth, when it has observed nothing at all.
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:not [ sh:property [ sh:path sosa:hasSimpleResult ;
                                       sh:minInclusive ?floor ; sh:maxInclusive ?ceiling ] ] ] ;
            sh:message "a reading sits outside the survival envelope for a property this agent holds — the subject is past tolerating, not merely uncomfortable" ] } }
$given
WHERE  {
    { SELECT ?agent ?property ?subject (MAX(?min) AS ?low) (MIN(?max) AS ?high) WHERE {
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
      } GROUP BY ?agent ?property ?subject }
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
    #  After the subqueries, because a BIND sees only what its own group has bound so far —
    #  the scope rule plan.rq met the hard way (#206).
    ?agent ag:localId ?who .
    BIND(IRI(CONCAT("http://example.org/agora#bounds.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?property), "#")))) AS ?bounds)
    BIND(IRI(CONCAT("http://example.org/agora#envelope.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?property), "#")))) AS ?envelope)
}
