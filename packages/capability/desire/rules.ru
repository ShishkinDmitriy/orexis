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
} ;

#  1c. The freshness want: a reading exists, and it is still evidence about NOW (#240).
#
#  A SHAPE OF ITS OWN, not a fourth property shape on the region, and the reason is structural
#  before it is conceptual: `sh:sparql` is a constraint on a NODE shape, and it has to be SPARQL
#  because SHACL core compares against a literal written in the shape while the horizon moves —
#  the agent re-commands its cadence whenever urgency does. So it could not have been a
#  `sh:property` beside the three declarative ones even if that had been wanted.
#
#  It is also a different KIND of want, which is the conceptual half. The region is about the
#  world (is the number where it should be); this is about the agent's knowledge of it (is the
#  number still worth anything). They are repaired by different means — no lever moves a number
#  you cannot see — and they must be droppable independently, which the next paragraph needs.
#
#  ONLY WHERE A SENSOR EXISTS, which is the decision this rule takes. An epistemic want in a
#  property nothing measures could never be satisfied: it would sit at maximum urgency for
#  ever, top every ranking an operator or a model reads, and inflate the `unactionable` count
#  the dashboards carry — training a reader to ignore the top row, which is the failure that
#  count exists to prevent. The case is already reported, once, by the shape that says "a
#  desire in a property this agent polls no sensor for" — `world/loner`'s zz plant states
#  ranges for light and humidity nothing reads, and gets three such warnings today. A permanent
#  maximal want would be a second and noisier way of saying what is already said.
#
#  The horizon is READ, never recomputed: `stale_after_s` works it out from the rhythm in force
#  and `publish_horizon` writes it into the instruments graph. A shape that recomputed it would
#  be a second definition free to drift; one that baked it would be wrong within a tick.
INSERT { GRAPH $into(ag:BoundsGraph) {
    ?agent ag:holds ?fresh .
    ?fresh a sh:NodeShape ;
        sh:targetNode ?agent ;
        ssn:forProperty ?property ;
        #  BOTH, because a sensor is the reason this want exists and the subject is what it is
        #  about — and an agent may poll instruments pointed at things it does not act for.
        prov:wasDerivedFrom ?sensor , ?subject ;
        ag:violationIs ag:Stale ;
        #  ON THE NODE SHAPE, and that is the opposite of where the declarative wants carry it.
        #  Measured on pySHACL 0.40.1, both ways round: a `sh:sparql` constraint's own
        #  `sh:severity` is IGNORED and the result comes back `sh:Violation`, while the node
        #  shape's is honoured; for a core `sh:property` constraint it is the other way about,
        #  which is why the region's three shapes carry theirs individually. Getting this wrong
        #  is not cosmetic — a want reported as a violation refuses the agent's boot, which is
        #  the one thing a want must never do, and it did exactly that before this line moved.
        sh:severity ag:ShouldBecome ;
        sh:sparql [
            #  Kept here too: it is what the spec says, so a conformant engine reads it, and a
            #  reader of this shape should not have to know our engine's quirk to see the force.
            sh:severity ag:ShouldBecome ;
            sh:message ?tooOld ;
            sh:select ?staleQuery ] } }
$given
WHERE  {
    #  THE PREMISE IS THE INSTRUMENT, not the stake, and the difference is not academic: the
    #  loner's gardener polls a water butt it does not act for. Tying this to the subject's
    #  stated ranges — the region's premise — left the butt's level with no freshness want, and
    #  since the keeper now pursues goals rather than sweeping noticed gaps, nothing would have
    #  watched it at all. `notices()` covered every sensor, and the want that replaces it must
    #  cover exactly the same ground.
    #
    #  It is also the honest premise on its own terms. Wanting a reading to be current is about
    #  the instrument and what it is pointed at: if this agent went to the trouble of polling
    #  something, it wants to know what that thing reads NOW. A stake is what makes the VALUE
    #  matter; a sensor is what makes the reading knowable, and this want is about knowing.
    ?agent a ag:Agent ; ag:localId ?who ; sensing:polls ?sensor .
    ?sensor sensing:monitors ?subject ; sosa:observes ?property .
    BIND(STRAFTER(STR(?property), "#") AS ?name)
    #  Keyed by the SENSOR, not by the property: one agent may poll two instruments reading the
    #  same property of different subjects — the loner's gardener does not, but the dealer's
    #  shape of world does, and a name that collided would silently merge two wants into one.
    BIND(IRI(CONCAT("http://example.org/agora#fresh.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?sensor), "#")))) AS ?fresh)
    BIND(CONCAT(?name, " was last read longer ago than ", ?who,
                " trusts a reading of it — the number is no longer evidence about now")
         AS ?tooOld)
    BIND(CONCAT(
      "SELECT $this ?value WHERE { ",
      "?obs <http://www.w3.org/ns/sosa/hasFeatureOfInterest> <", STR(?subject), "> ; ",
      "<http://www.w3.org/ns/sosa/observedProperty> <", STR(?property), "> ; ",
      "<http://www.w3.org/ns/sosa/resultTime> ?at ; ",
      "<http://www.w3.org/ns/sosa/hasSimpleResult> ?value . ",
      "<", STR(?sensor), "> <http://example.org/agora/sensing#staleAfterS> ?horizon . ",
      "FILTER(?at + STRDT(CONCAT(\"PT\", STR(?horizon), \"S\"), ",
      "<http://www.w3.org/2001/XMLSchema#dayTimeDuration>) < NOW()) }") AS ?staleQuery)
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
        #  NOT LOOKED. Existence alone, so an unmeasured property reports exactly one thing and
        #  it is the true one. The two side shapes below cannot say this: each asks whether a
        #  reading is outside its edge, and no reading is outside anything.
        sh:property [
            sh:severity ag:ShouldBecome ;
            sh:path ( ag:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            ag:violationIs ag:Unmeasured ;
            sh:qualifiedMinCount 1 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ] ;
            sh:message ?unseen ] ;
        #  BELOW, and ABOVE, as two shapes rather than one range test inside a qualified shape.
        #  The old form violated `QualifiedMinCount` — "no conforming reading exists" — which
        #  is true of a drowning plant and a dying one alike, and watering repairs one of them.
        #  A means will declare which violations it repairs (#239), a message can name the side
        #  it is about, and a dashboard stops showing the two as one row.
        sh:property [
            sh:severity ag:ShouldBecome ;
            sh:path ( ag:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            ag:violationIs ag:Below ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:maxExclusive ?low ] ] ;
            sh:message ?tooLow ] ;
        sh:property [
            sh:severity ag:ShouldBecome ;
            sh:path ( ag:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            ag:violationIs ag:Above ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:minExclusive ?high ] ] ;
            sh:message ?tooHigh ] .
    ?envelope a sh:NodeShape ;
        sh:targetNode ?agent ;
        ssn:forProperty ?property ;
        prov:wasDerivedFrom ?subject ;
        #  A WARNING and not a violation, which is the difference between "this world is
        #  illegitimate" and "this plant is dying". Refusing here would stop an agent booting
        #  exactly when its subject most needs it — and the envelope's real work is scaling
        #  urgency, which happens whether or not anything is validated.
        #
        #  NO observation may sit past either edge — where the region demands that one exist at
        #  all. The asymmetry is about evidence: not knowing is a gap an agent closes by
        #  looking, but silence is not evidence that a subject is past tolerating, and a shape
        #  that said so would have every agent reporting catastrophe at birth.
        #
        #  Two shapes here too, and splitting them cost nothing but bought the `sh:not` back:
        #  "outside the range" needed a negation, "past this edge" is `sh:maxExclusive`.
        sh:property [
            sh:severity sh:Warning ;
            sh:path ( ag:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            ag:violationIs ag:Below ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:maxExclusive ?floor ] ] ;
            sh:message ?underFloor ] ;
        sh:property [
            sh:severity sh:Warning ;
            sh:path ( ag:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            ag:violationIs ag:Above ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:minExclusive ?ceiling ] ] ;
            sh:message ?overCeiling ] } }
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

    #  The messages, with the property and the numbers IN them. A shape is minted per (agent,
    #  property), so a message written here is already about one property and one region — no
    #  templating engine required, and none available: pySHACL interpolates `{$var}` only for
    #  `sh:sparql` constraints, measured, and these are declarative on purpose.
    #
    #  What cannot be baked in is the offending VALUE, which is not known until validation.
    #  That one is answered where it belongs — `gap.rq` reports value, region and signed
    #  distance together, and a report is for saying WHAT is wrong, not how far.
    BIND(STRAFTER(STR(?property), "#") AS ?name)
    BIND(CONCAT("nothing has read ", ?name, " for ", ?who,
                " — an unmeasured want is a gap, and the first intention is to look")
         AS ?unseen)
    BIND(CONCAT(?name, " is below ", STR(?low), ", the floor of the region deduced for ",
                ?who, " (", STR(?low), "-", STR(?high), ")") AS ?tooLow)
    BIND(CONCAT(?name, " is above ", STR(?high), ", the ceiling of the region deduced for ",
                ?who, " (", STR(?low), "-", STR(?high), ")") AS ?tooHigh)
    BIND(CONCAT(?name, " is below ", STR(?floor), " — past what ", ?who,
                " survives, not merely uncomfortable") AS ?underFloor)
    BIND(CONCAT(?name, " is above ", STR(?ceiling), " — past what ", ?who,
                " survives, not merely uncomfortable") AS ?overCeiling)
}
