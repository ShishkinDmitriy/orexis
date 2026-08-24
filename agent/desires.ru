# Derivation: what this agent WANTS — run by the desires build, never by genesis (#312).
#
# The regions, the envelopes and the freshness wants used to be derived at genesis into the
# belief base's constraint graph, and the desires store copied them. The copy is gone: the
# desire modality derives its own content on every rebuild — boot, a re-pick, an obligation
# transition — so a want whose premise has ceased is absent afterwards because the derivation
# no longer implies it, which is #263's discipline running live rather than once.
#
# `$me` is the one agent this modality belongs to, `$derived` the build's own derived-wants
# graph and `$given` its premises, substituted by
# `agent/desire.py` exactly as genesis substitutes its rules: a rule says what it concludes,
# never where. The grant rules stayed in `rules.ru` — a grant is a fact about the AGENT and
# is genesis's to derive; what the agent wants is the modality's.

PREFIX desire: <http://example.org/orexis/desire#>
PREFIX market: <http://example.org/orexis/market#>
PREFIX actuation: <http://example.org/orexis/actuation#>
PREFIX sensing: <http://example.org/orexis/sensing#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ag:   <http://example.org/orexis#>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>

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
#  REIFIED like the region below (a-desire-states-its-own-measure): the desire is a node, and
#  the met-test hangs off it as `ag:metWhen`. What this one does NOT carry is a measure — an
#  epistemic want has no distance to scale (a boolean and an age, both already judged where the
#  clock is), and routing freshness goals through the search is the seam the measure record
#  leaves open. Its urgency stays the kernel's: 1.0 unmeasured or stale, 0.0 otherwise.
INSERT { GRAPH $derived {
    $me ag:holds ?fresh .
    ?fresh a ag:Desire ;
        ssn:forProperty ?property ;
        #  BOTH, because a sensor is the reason this want exists and the subject is what it is
        #  about — and an agent may poll instruments pointed at things it does not act for.
        prov:wasDerivedFrom ?sensor , ?subject ;
        ag:violationIs ag:Stale ;
        rdfs:label ?freshLabel ;
        ag:metWhen ?freshMet .
    ?freshMet a sh:NodeShape ;
        sh:targetNode $me ;
        ssn:forProperty ?property ;
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
    #  since the keeper now pursues desires rather than sweeping noticed gaps, nothing would have
    #  watched it at all. `notices()` covered every sensor, and the want that replaces it must
    #  cover exactly the same ground.
    #
    #  It is also the honest premise on its own terms. Wanting a reading to be current is about
    #  the instrument and what it is pointed at: if this agent went to the trouble of polling
    #  something, it wants to know what that thing reads NOW. A stake is what makes the VALUE
    #  matter; a sensor is what makes the reading knowable, and this want is about knowing.
    $me a ag:Agent ; ag:localId ?who ; sensing:polls ?sensor .
    ?sensor sensing:monitors ?subject ; sosa:observes ?property .
    BIND(STRAFTER(STR(?property), "#") AS ?name)
    #  Keyed by the SENSOR, not by the property: one agent may poll two instruments reading the
    #  same property of different subjects — the loner's gardener does not, but the dealer's
    #  shape of world does, and a name that collided would silently merge two wants into one.
    BIND(IRI(CONCAT("http://example.org/orexis#fresh.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?sensor), "#")))) AS ?fresh)
    BIND(IRI(CONCAT(STR(?fresh), ".met")) AS ?freshMet)
    BIND(CONCAT(?name, " read recently enough to be evidence about now, through ",
                STRAFTER(STR(?sensor), "#")) AS ?freshLabel)
    BIND(CONCAT(?name, " was last read longer ago than ", ?who,
                " trusts a reading of it — the number is no longer evidence about now")
         AS ?tooOld)
    BIND(CONCAT(
      "SELECT $this ?value WHERE { ",
      "?obs <http://www.w3.org/ns/sosa/hasFeatureOfInterest> <", STR(?subject), "> ; ",
      "<http://www.w3.org/ns/sosa/observedProperty> <", STR(?property), "> ; ",
      "<http://www.w3.org/ns/sosa/resultTime> ?at ; ",
      "<http://www.w3.org/ns/sosa/hasSimpleResult> ?value . ",
      "<", STR(?sensor), "> <http://example.org/orexis/sensing#staleAfterS> ?horizon . ",
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
#  thing nothing can reference, and an intention must be able to say which desire it serves.
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
#  REIFIED since a-desire-states-its-own-measure: the DESIRE is a node of its own, and the
#  met-shape hangs off it (`ag:metWhen`) instead of being it. The shape's content is unchanged
#  — what changed is that the desire now has room on it for what a bare shape could not carry:
#  a label a dashboard or the ask channel can print, and a place for a measure to hang.
#
#  NO MEASURE IS WRITTEN HERE, and the absence is the sovereign's ruling rather than an
#  omission: the core is BDI, so this derivation minting the want, its shape and its node is
#  the mind's structure — and how badness is MEASURED is planning-domain machinery, a
#  capability's contribution the kernel only ASKS for, through the choir
#  (Module.desire_urgency). Sensing declares the measure for observation-backed wants in its
#  own `measures.ttl`, in its own namespace, read by its own code; the kernel holds no
#  measure vocabulary, no measure graph, no evaluator.
INSERT { GRAPH $derived {
    $me ag:holds ?desire , ?envelope .
    ?desire a ag:Desire ;
        ssn:forProperty ?property ;
        prov:wasDerivedFrom ?subject ;
        rdfs:label ?label ;
        rdfs:comment ?describes ;
        ag:metWhen ?bounds .
    ?bounds a sh:NodeShape ;
        sh:targetNode $me ;
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
        sh:targetNode $me ;
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
    { SELECT ?property ?subject (MAX(?min) AS ?low) (MIN(?max) AS ?high) WHERE {
        $me a ag:Agent ; ag:actsFor ?subject .
        ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?need .
        ?need ssn:forProperty ?property .
        { ?subject ssn-system:hasOperatingRange ?range }
        UNION
        { ?instrument sensing:monitors ?subject ; ssn-system:hasOperatingRange ?range }
        ?range ssn-system:inCondition ?condition .
        ?condition ssn:forProperty ?property ;
                   schema:minValue ?min ;
                   schema:maxValue ?max .
      } GROUP BY ?property ?subject }
    OPTIONAL {
      SELECT ?property (MAX(?least) AS ?floor) (MIN(?most) AS ?ceiling) WHERE {
        $me a ag:Agent ; ag:actsFor ?subject .
        ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?need .
        ?need ssn:forProperty ?property .
        { ?subject ssn-system:hasSurvivalRange ?envelope }
        UNION
        { ?instrument sensing:monitors ?subject ; ssn-system:hasSurvivalRange ?envelope }
        ?envelope ssn-system:inCondition ?tolerated .
        ?tolerated ssn:forProperty ?property ;
                   schema:minValue ?least ;
                   schema:maxValue ?most .
      } GROUP BY ?property }
    FILTER(?low <= ?high)
    #  After the subqueries, because a BIND sees only what its own group has bound so far —
    #  the scope rule plan.rq met the hard way (#206).
    $me ag:localId ?who .
    BIND(IRI(CONCAT("http://example.org/orexis#desire.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?property), "#")))) AS ?desire)
    BIND(IRI(CONCAT("http://example.org/orexis#bounds.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?property), "#")))) AS ?bounds)
    BIND(IRI(CONCAT("http://example.org/orexis#envelope.", ENCODE_FOR_URI(?who), ".",
                    ENCODE_FOR_URI(STRAFTER(STR(?property), "#")))) AS ?envelope)

    #  For the description only — the measure reads nothing baked. The centre is the no-pick
    #  fallback target: where an agent with no other reason to prefer would aim.
    BIND((?low + ?high) / 2 AS ?centre)

    #  The aim, if one is already picked — for the LABEL only. The measure never bakes it: it
    #  reads $beliefs at query time, which is what lets a re-pick move the urgency between
    #  rebuilds. The label is refreshed on rebuild, which every recorded re-pick triggers.
    OPTIONAL { $me ag:aims ?aimed . ?aimed ssn:forProperty ?property ; schema:value ?picked }
    BIND(CONCAT(?name, " inside ", STR(?low), "-", STR(?high),
                COALESCE(CONCAT(", aiming ", STR(?picked)), ", no aim picked yet"))
         AS ?label)
    BIND(CONCAT(?who, " holds ", ?name, " of ", STRAFTER(STR(?subject), "#"),
                " inside ", STR(?low), "-", STR(?high),
                "; urgency is the distance from its aim (the centre, ", STR(?centre),
                ", while none is picked), scaled by the survival room on that side")
         AS ?describes)

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
