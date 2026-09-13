# Derivation: what an agent wants ABOUT ITS OWN KNOWLEDGE — one want per instrument it polls.
#
# HERE AND NOT IN THE KERNEL, which is where this rule lived until now. The mind stays the
# kernel's — that an agent wants, what a want is, when one is met (the-mind-is-not-a-package) —
# and the kernel goes on deriving the REGION want, whose premise is the ranges a world states
# about a subject. This one's premise is an INSTRUMENT: it exists because this agent polls
# something, and it is repaired by asking that something for a reading. Both of those are
# sensing's facts, in sensing's namespace, and the kernel spelled two of them out as strings to
# state a want it could not otherwise say. Moving the rule takes four package IRIs out of the
# kernel (#334's ratchet) and puts the horizon term back beside the code that publishes it.
#
# Run by the desire modality's build like every `desires.ru`, with `$me`, `$given` and
# `$derived` substituted by `orexis_modality_graph/desire.py`. The grant rules stay in `rules.ru`: what an
# agent CAN DO is genesis's, what it WANTS is the modality's, and this package now ships both.

PREFIX sensing: <http://example.org/orexis/sensing#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX orexis:   <http://example.org/orexis#>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>

#  The freshness want: a reading of this exists, and it was taken recently enough to be about
#  NOW. Stated POSITIVELY, and that is this rule's one substantive change (#342).
#
#  It used to say the opposite thing — violated where an observation exists whose `resultTime`
#  plus the horizon has passed — and a shape that hunts for a bad reading is satisfied by the
#  absence of any reading at all. Two ways of having nothing then read as met: a property
#  nobody has ever looked at, and a sensor whose horizon has not been published, which is every
#  sensor before its module's first `publish_horizon`. Measured on pySHACL 0.40.1 by taking the
#  horizon triple away: `conforms` flipped from False to True, so the agent believed every
#  reading current for ever and nothing anywhere was red. Saying what the agent WANTS rather
#  than what would disappoint it fixes both at the root — with no observation, or with no
#  horizon to judge one against, the inner pattern binds nothing, the NOT EXISTS holds, and the
#  want reports unmet, which is the loud direction.
#
#  It also states the thing an Observe can REPAIR, which is what makes this a goal the search
#  can reach rather than a state a special case had to recognise. Sensing's effect predicts an
#  observation stamped NOW() and carrying whatever value was last seen — on a first look, no
#  value at all — so the pattern below is deliberately silent about `sosa:hasSimpleResult`: a
#  look that returns nothing knowable still ends the not-having-looked, and demanding a result
#  would make the one honest effect unable to satisfy the want it exists for.
#
#  SPARQL and not SHACL core, for the reason the plan record gives: core compares against a
#  literal written IN the shape and "within the last N seconds" needs *now*. That is decided per
#  goal KIND by whether anything reads numbers out of it, and nothing reads numbers out of this
#  one — the measure beside it in `measures.ttl` answers how badly, and answers it against
#  whichever world is being judged.
#
#  ONLY WHERE A SENSOR EXISTS, which is the decision this rule takes and keeps. An epistemic
#  want in a property nothing measures could never be satisfied: it would sit at maximum urgency
#  for ever, top every ranking an operator or a model reads, and inflate the `unactionable`
#  count the dashboards carry — training a reader to ignore the top row, which is the failure
#  that count exists to prevent. The case is already reported once, by the shape that says "a
#  desire in a property this agent polls no sensor for".
#
#  The horizon is READ, never recomputed: `stale_after_s` works it out from the rhythm in force
#  and `publish_horizon` writes it into the instruments graph. A shape that recomputed it would
#  be a second definition free to drift; one that baked it would be wrong within a tick.
INSERT { GRAPH $derived {
    $me orexis:holds ?fresh .
    ?fresh a orexis:Desire , sensing:Freshness ;
        orexis:bindsWhen orexis:Always ;
        ssn:forProperty ?property ;
        orexis:about ?sensor ;
        #  THE SENSOR ALONE, and the subject is reached through it. This carried both for a
        #  while, on the reasoning that a want is about the thing as much as about the
        #  instrument — and `desires.rq` binds the instrument off `prov:wasDerivedFrom`, so two
        #  premises meant two rows, one of them keyed on a subject no instruments table has and
        #  therefore permanently unmeasured. One want, one premise, one row.
        prov:wasDerivedFrom ?sensor ;
        orexis:violationIs orexis:Stale ;
        rdfs:label ?freshLabel ;
        orexis:metWhen ?freshMet .
    ?freshMet a sh:NodeShape ;
        sh:targetNode $me ;
        ssn:forProperty ?property ;
        #  NO severity, since #472: a met-test enters no validation pass — the metWhen
        #  linkage takes it out in `conformance.py` — so it needs no force to be survivable,
        #  and the severity that used to mark it as a want retired with the era when a desire
        #  WAS a bare shape. The planner validates this shape directly and reads results at
        #  whatever severity the engine defaults to.
        sh:sparql [
            #  THE DICTIONARY, in SHACL's own words (#508): a `sh:select` may use a prefixed
            #  name only where the constraint points at a node carrying one `sh:declare` per
            #  prefix, and every shape in this tree points at `orexis:` itself, which the
            #  store assembles and travels with every shapes graph either engine is handed.
            #  Without it the select below would have to spell every IRI in full, which is
            #  what it did.
            sh:prefixes orexis: ;
            sh:message ?tooOld ;
            sh:select ?staleQuery ] } }
$given
WHERE  {
    #  THE PREMISE IS THE INSTRUMENT, not the stake, and the difference is not academic: the
    #  loner's gardener polls a water butt it does not act for. Tying this to the subject's
    #  stated ranges — the region's premise — left the butt's level with no freshness want, and
    #  since the keeper pursues desires rather than sweeping noticed gaps, nothing would have
    #  watched it at all. `notices()` covered every sensor, and the want that replaces it must
    #  cover exactly the same ground.
    #
    #  It is also the honest premise on its own terms. Wanting a reading to be current is about
    #  the instrument and what it is pointed at: if this agent went to the trouble of polling
    #  something, it wants to know what that thing reads NOW. A stake is what makes the VALUE
    #  matter; a sensor is what makes the reading knowable, and this want is about knowing.
    $me a orexis:Agent ; orexis:localId ?who ; sensing:polls ?sensor .
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
    BIND(CONCAT("nothing ", ?who, " trusts says what ", ?name, " reads now — either ",
                STRAFTER(STR(?sensor), "#"),
                " has never reported it, or the last time it did is further back than the ",
                "horizon in force") AS ?tooOld)
    #  MADE BY THIS INSTRUMENT, which is the clause that keeps this an epistemic want. The
    #  want is keyed by the sensor and its label says "through" it, and the shape said nothing
    #  about the sensor at all — so any observation of the pair satisfied it, including the one
    #  a DOSE's effect predicts. Every effect that moves a number states it as a reading,
    #  because predicting a value is the only way to say a value changed; only a look states
    #  who saw it. Watering does not tell you how wet the soil is, and a shape that cannot say
    #  so lets a thirsty plant answer a stale reading by buying water — which it did, once, in
    #  the pass that found this.
    #  UNMET WHILE NO READING OF MINE IS EVIDENCE, and evidence is a FACT rather than an age
    #  (#598): sensing writes `staleSince` on a reading when the horizon runs out, so this asks
    #  for a reading by this instrument that does not carry it. It computed `?at + horizon >
    #  NOW()` until then — the real clock, asked of every world a search imagines.
    BIND(CONCAT(
      "SELECT $this WHERE { FILTER NOT EXISTS { ",
      "?obs sosa:hasFeatureOfInterest <", STR(?subject), "> ; ",
      "sosa:observedProperty <", STR(?property), "> ; ",
      "sosa:madeBySensor <", STR(?sensor), "> . ",
      "FILTER NOT EXISTS { ?obs sensing:staleSince ?since } } }") AS ?staleQuery)
}
;

#################  The stake: the region, and the envelope around it  #################
#
#  Was `agent/desires.ru`, the kernel's — and the kernel's last `sosa`. The want is derived
#  from what the subject STATES IT NEEDS (`ssn-system:hasOperatingRange`, narrowed by every
#  instrument that monitors it) and met by an OBSERVATION of it sitting inside — both sensing's
#  facts, in sensing's words, which is why the rule is here (the-stake-is-sensings-want). The
#  node IRIs are unchanged: `orexis:desire.<who>.<property>`, `orexis:bounds.…`, `orexis:envelope.…`, so
#  a ledger row that names one still resolves.
#
#  AUTHORED AT GENESIS, NEVER REBUILT (#644, a-root-holds-always-and-an-outdated-graph-is-dropped):
#  a root is a declaration for the agent's whole life, so these rules run at birth into the
#  agent's roots graph — `$derived` is that graph there — and again at boot to ENDOW a root an
#  amendment added, a held one staying whatever the world now says. Nothing of the agent's own
#  state enters: the foresight is the choir's answer when a child is derived, and the aim is
#  read by the measure, so the label names the region and no pick.
#
#  TWO NODE SHAPES per property, told apart by the FORCE they carry: the region, a violation of
#  which is a gap, and the envelope, a violation of which is the subject ending. Within each the
#  edges live on the SIDE shapes, so a violation says WHICH WAY it went — see
#  orexis:violationIs. BY BAND since #579: a side shape asks whether a reading of the property
#  is a `sensing:BelowRegion` or an `AboveRegion` — the class the domain asserts on a reading,
#  a real one from its number and a predicted one from its effect — and not whether a number
#  sits past an edge. One number apiece used to live here (#242); the region's numbers live in
#  the bands' definitions now, minted from the same range.
#
#  THE ENVELOPE STILL ASKS BY NUMBER, and that is the sovereign's three-band ruling arriving
#  here: the survival range mints no band, so past-the-envelope is not something a reading IS.
#  It is a warning about a reading the world actually holds, asked at the gates where a number
#  is there to ask about; an imagined world states what a reading is and no number, so this
#  shape is silent there — correctly, since what a plan may not pass through is the law, and a
#  warning is not one.
INSERT { GRAPH $derived {
    $me orexis:holds ?desire , ?envelope .
    ?desire a orexis:Desire ;
        orexis:bindsWhen orexis:Always ;
        ssn:forProperty ?property ;
        orexis:about ?property ;
        prov:wasDerivedFrom ?subject ;
        rdfs:label ?label ;
        rdfs:comment ?describes ;
        orexis:metWhen ?bounds .
    ?bounds a sh:NodeShape ;
        sh:targetNode $me ;
        ssn:forProperty ?property ;
        prov:wasDerivedFrom ?subject ;
        #  NOT LOOKED. Existence alone, so an unmeasured property reports exactly one thing and
        #  it is the true one. The two side shapes below cannot say this: each asks whether a
        #  reading is outside its edge, and no reading is outside anything.
        sh:property [
            sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            orexis:violationIs orexis:Unmeasured ;
            sh:qualifiedMinCount 1 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                #  A reading that IS some band (#579): one a look imagined with nothing in it
                #  is no evidence, and counted it as measured a look would meet every want.
                sh:or ( [ sh:class sensing:BelowRegion ] [ sh:class sensing:InRegion ]
                        [ sh:class sensing:AboveRegion ] ) ] ;
            sh:message ?unseen ] ;
        #  BELOW, and ABOVE, as two shapes rather than one range test inside a qualified shape.
        #  The old form violated `QualifiedMinCount` — "no conforming reading exists" — which
        #  is true of a drowning plant and a dying one alike, and watering repairs one of them.
        #  A means will declare which violations it repairs (#239), a message can name the side
        #  it is about, and a dashboard stops showing the two as one row.
        sh:property [
            sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            orexis:violationIs orexis:Below ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:class sensing:BelowRegion ] ;
            sh:message ?tooLow ] ;
        sh:property [
            sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            orexis:violationIs orexis:Above ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:class sensing:AboveRegion ] ;
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
            sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            orexis:violationIs orexis:Below ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:maxExclusive ?floor ] ] ;
            sh:message ?underFloor ] ;
        sh:property [
            sh:severity sh:Warning ;
            sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
            orexis:violationIs orexis:Above ;
            sh:qualifiedMaxCount 0 ;
            sh:qualifiedValueShape [
                sh:property [ sh:path sosa:observedProperty ; sh:hasValue ?property ] ;
                sh:property [ sh:path sosa:hasSimpleResult ; sh:minExclusive ?ceiling ] ] ;
            sh:message ?overCeiling ] } }
$given
WHERE  {
    #  NO FORESIGHT HERE (#644): how far ahead this agent acts on a predicted crossing is a
    #  belief it may re-pick, and a root is not a function of its state — pursuit asks the
    #  choir (`orexis:foresight`) when it derives, and sensing answers from the belief then.
    { SELECT ?property ?subject (MAX(?min) AS ?low) (MIN(?max) AS ?high) WHERE {
        $me a orexis:Agent ; orexis:actsFor ?subject .
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
        $me a orexis:Agent ; orexis:actsFor ?subject .
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
    $me orexis:localId ?who .
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
    #  NO AIM IN THE LABEL either: the aim is a pick the measure reads at query time, and a
    #  root authored once must not bake the pick of the day it was born (#644).
    BIND(CONCAT(?name, " inside ", STR(?low), "-", STR(?high)) AS ?label)
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
