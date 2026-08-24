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
# `$derived` substituted by `agent/desire.py`. The grant rules stay in `rules.ru`: what an
# agent CAN DO is genesis's, what it WANTS is the modality's, and this package now ships both.

PREFIX sensing: <http://example.org/orexis/sensing#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ag:   <http://example.org/orexis#>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>

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
    $me ag:holds ?fresh .
    ?fresh a ag:Desire , sensing:Freshness ;
        ssn:forProperty ?property ;
        #  THE SENSOR ALONE, and the subject is reached through it. This carried both for a
        #  while, on the reasoning that a want is about the thing as much as about the
        #  instrument — and `desires.rq` binds the instrument off `prov:wasDerivedFrom`, so two
        #  premises meant two rows, one of them keyed on a subject no instruments table has and
        #  therefore permanently unmeasured. One want, one premise, one row.
        prov:wasDerivedFrom ?sensor ;
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
    #  since the keeper pursues desires rather than sweeping noticed gaps, nothing would have
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
    BIND(CONCAT(
      "SELECT $this WHERE { FILTER NOT EXISTS { ",
      "?obs <http://www.w3.org/ns/sosa/hasFeatureOfInterest> <", STR(?subject), "> ; ",
      "<http://www.w3.org/ns/sosa/observedProperty> <", STR(?property), "> ; ",
      "<http://www.w3.org/ns/sosa/madeBySensor> <", STR(?sensor), "> ; ",
      "<http://www.w3.org/ns/sosa/resultTime> ?at . ",
      "<", STR(?sensor), "> <http://example.org/orexis/sensing#staleAfterS> ?horizon . ",
      "FILTER(?at + STRDT(CONCAT(\"PT\", STR(?horizon), \"S\"), ",
      "<http://www.w3.org/2001/XMLSchema#dayTimeDuration>) > NOW()) } }") AS ?staleQuery)
}
