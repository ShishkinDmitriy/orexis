# Derivation: which sensing capability an agent gets, from the DEVICE'S NATURE.
#
# One fact decides it — WHO HOLDS THE CLOCK. Can the device be asked at any moment, does it
# take an interval and keep to it, or does it announce on its own? That is a property of the
# hardware and its firmware, not of anyone's opinion, so an agent's ability can never drift
# from its equipment. Reflash a board from push to scheduled, re-run genesis, and the agent
# gains an interval to state with no edit to the agent, because there is nothing about it to
# edit.
#
# sensing:PolledProcedure -> sensing:Polling is deliberately ABSENT. The vocabulary declares both, because there
# are three ways to hold a clock and the T-Box should say so; but no board here is always
# reachable, and granting a capability no module implements would only produce a startup
# warning. The rule is the last piece to add, not the first.
#
# Note what is NOT consulted: how the device is spoken to. A pull board on MQTT and one on a
# GPIO pin give their agent the same ability and the same decisions; only the driver differs.
# Whether a given binding is COMPLETE (a pull sensor on a bus needs a command channel) is a
# question for that transport's shapes, not for this rule.

PREFIX sensing: <http://example.org/orexis/sensing#>
PREFIX mqtt: <http://example.org/orexis/mqtt#>
PREFIX unit: <http://qudt.org/vocab/unit/>
PREFIX schema: <https://schema.org/>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX review: <http://example.org/orexis/review#>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX orexis:   <http://example.org/orexis#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX ssn: <http://www.w3.org/ns/ssn/>

#  Both rules ask what a thing IS, literally — no `rdfs:subClassOf*` walk, because the
#  vocabulary's entailments are asserted before any rule runs (orexis/inference.py). What they
#  cannot do is name one graph: `sensing:polls` is the sovereign's and `a sensing:Sensor` may be entailed,
#  so the two facts live apart and a single `GRAPH` clause would match neither pair. `$given`
#  becomes the `USING` clauses that merge what is GIVEN — asserted and entailed — and
#  deliberately not what another rule derived. `$derived` is where conclusions land. Both are
#  substituted by the loader: a graph IRI is an instance, and a rule should not name one.
#
#  The answers go to the DERIVED graph. See knowledge/decisions/who-put-the-fact-there.md.

#  Keeps to an interval it is given -> the agent STATES that interval.
#
#  The mode is the DEVICE's (#96) — the thing that connects and keeps the clock — and a sensor
#  reaches it through the stream they share. A device is its own carrier (it states the topic it
#  speaks on), so the join covers the board itself and every peripheral riding its wire alike.
#  mqtt terms in a sensing rule, honestly: today the only carrier IS the bus, and the day a
#  second transport exists, "shares the device's stream" needs a transport-neutral word here.
INSERT { GRAPH $derived {
    ?agent orexis:hasCapability sensing:Subscribing } }
$given
WHERE  { ?agent sensing:polls ?sensor . ?sensor a sosa:Sensor ; mqtt:readingTopic ?stream .
         ?device mqtt:readingTopic ?stream ; mqtt:onBus ?bus ;
                 sensing:senseMode sensing:ScheduledProcedure } ;

#  Announces on its own clock -> the agent can only RECEIVE, and is never asked for a cadence.
INSERT { GRAPH $derived {
    ?agent orexis:hasCapability sensing:Listening } }
$given
WHERE  { ?agent sensing:polls ?sensor . ?sensor a sosa:Sensor ; mqtt:readingTopic ?stream .
         ?device mqtt:readingTopic ?stream ; mqtt:onBus ?bus ;
                 sensing:senseMode sensing:PushProcedure } ;

#  Keeps to an interval it is given -> the agent may also ASK, and that is a different fact
#  from being allowed to read it.
#
#  `sensing:polls` is the access grant and it is granted for both clocks alike, because
#  receiving is reading. What varies is whether traffic can go the other way: a device keeping
#  a schedule it was handed can be interrupted with a `sense` nudge, best-effort; a device
#  keeping its own clock has nothing that would hear one. `affordances.rq` offers Observe off
#  THIS rather than off `polls`, so a listening agent's menu does not carry a lever that does
#  nothing when pulled — which is what it carried until now: the row existed, the keeper
#  adopted the intention, `sense_now()` returned having done nothing, and the commitment stood
#  until patience outwaited it. Silent, and repeating for ever.
#
#  ONE MODE, matching the one grant above it, and the pairing is why they sit together.
#  `sensing:PolledProcedure` belongs here too by its nature — a device reachable at any moment
#  is the one that can best be asked — and it is deliberately absent for the same reason no
#  rule grants `sensing:Polling`: nothing implements the asking, so the row would be a lever
#  whose executor does not exist. The two lines land together or not at all.
INSERT { GRAPH $derived {
    ?agent sensing:mayAsk ?sensor } }
$given
WHERE  { ?agent sensing:polls ?sensor . ?sensor a sosa:Sensor ; mqtt:readingTopic ?stream .
         ?device mqtt:readingTopic ?stream ; mqtt:onBus ?bus ;
                 sensing:senseMode sensing:ScheduledProcedure } ;

#  What the EQUIPMENT allows, carried from the sensor to the agent that polls it.
#
#  An agent cannot ask its sensors what they can do — `ranges()` narrows a belief it holds, and
#  a belief is the agent's, so the limit has to reach the agent as a fact ABOUT THE AGENT. This
#  is the carry: whatever floor any sensor an agent polls declares becomes a floor on that
#  agent's cadence, because an agent polling two devices can go no faster than its slowest.
#
#  `MAX`, and that is the whole of the arithmetic. Two sensors on one agent, one honouring 30s
#  and one 60s, leave the agent with 60: a floor is the tightest constraint that binds, and
#  taking the min would let the slower board be asked for something it will never keep — which
#  is the exact failure this exists to prevent, arrived at from the other side.
#
#  Shaped as a review:Mandate because it narrows the same term the same way and `ranges()`
#  can then intersect both with one arithmetic. Under review:limitedTo and never
#  review:commits: one is what a board can do and the other what a sovereign allowed, and a
#  refused revision should say which of the two refused it.
INSERT { GRAPH $derived {
    ?agent review:limitedTo [ review:onTerm sensing:slowSleepS ; review:notBelow ?floor ] } }
$given
WHERE  {
    { SELECT ?agent (MAX(?s) AS ?floor) WHERE {
        ?agent sensing:polls ?sensor .
        ?sensor ssn-system:hasSystemCapability ?cap .
        ?cap ssn-system:hasSystemProperty ?freq .
        ?freq a ssn-system:Frequency ; schema:value ?s ; schema:unitCode unit:SEC .
      } GROUP BY ?agent }
} ;

#  WHAT A READING CAN BE, per (subject, property) that states a range (#576). The three bands
#  of the operating region as member classes of `sensing:BelowRegion`, `sensing:InRegion` and
#  `sensing:AboveRegion`, each defined in OWL — an intersection of the observation class, the
#  subject and the property by `owl:hasValue`, and the result by a datatype restriction — so
#  that a reader with an OWL reasoner sees exactly what `Store.entail` asserts. The region is
#  the same intersection `desires.ru` computes for the want: the highest floor and the lowest
#  ceiling any range applying to the subject states, its own or an instrument's. Two rules
#  reading one premise, the range; the class says what a reading IS, the want's shape what
#  must hold. Minted at GENESIS and public rather than in the desire modality's rebuild
#  because the sensed writer classifies a reading in the belief base, where the desire
#  modality's graphs are not. `onDatatype` documents the reading's type; the entailment
#  compares numerically, so a double reading is classified like a decimal one.
INSERT { GRAPH $derived {
    ?below a owl:Class ; rdfs:subClassOf sensing:BelowRegion ; rdfs:label ?belowLabel ;
        owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( sosa:Observation
            [ a owl:Restriction ; owl:onProperty sosa:hasFeatureOfInterest ; owl:hasValue ?subject ]
            [ a owl:Restriction ; owl:onProperty sosa:observedProperty ; owl:hasValue ?property ]
            [ a owl:Restriction ; owl:onProperty sosa:hasSimpleResult ;
              owl:someValuesFrom [ a rdfs:Datatype ; owl:onDatatype xsd:decimal ;
                                   owl:withRestrictions ( [ xsd:maxExclusive ?low ] ) ] ] ) ] .
    ?inside a owl:Class ; rdfs:subClassOf sensing:InRegion ; rdfs:label ?insideLabel ;
        owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( sosa:Observation
            [ a owl:Restriction ; owl:onProperty sosa:hasFeatureOfInterest ; owl:hasValue ?subject ]
            [ a owl:Restriction ; owl:onProperty sosa:observedProperty ; owl:hasValue ?property ]
            [ a owl:Restriction ; owl:onProperty sosa:hasSimpleResult ;
              owl:someValuesFrom [ a rdfs:Datatype ; owl:onDatatype xsd:decimal ;
                                   owl:withRestrictions ( [ xsd:minInclusive ?low ] [ xsd:maxInclusive ?high ] ) ] ] ) ] .
    ?above a owl:Class ; rdfs:subClassOf sensing:AboveRegion ; rdfs:label ?aboveLabel ;
        owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( sosa:Observation
            [ a owl:Restriction ; owl:onProperty sosa:hasFeatureOfInterest ; owl:hasValue ?subject ]
            [ a owl:Restriction ; owl:onProperty sosa:observedProperty ; owl:hasValue ?property ]
            [ a owl:Restriction ; owl:onProperty sosa:hasSimpleResult ;
              owl:someValuesFrom [ a rdfs:Datatype ; owl:onDatatype xsd:decimal ;
                                   owl:withRestrictions ( [ xsd:minExclusive ?high ] ) ] ] ) ] . } }
$given
WHERE {
    { SELECT ?property ?subject (MAX(?min) AS ?low) (MIN(?max) AS ?high) WHERE {
        ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?need .
        ?need ssn:forProperty ?property .
        { ?subject ssn-system:hasOperatingRange ?range }
        UNION
        { ?instrument sensing:monitors ?subject ; ssn-system:hasOperatingRange ?range }
        ?range ssn-system:inCondition ?condition .
        ?condition ssn:forProperty ?property ; schema:minValue ?min ; schema:maxValue ?max .
      } GROUP BY ?property ?subject }
    FILTER(?low <= ?high)
    BIND(CONCAT("http://example.org/orexis#band.", ENCODE_FOR_URI(STRAFTER(STR(?subject), "#")), ".",
                ENCODE_FOR_URI(STRAFTER(STR(?property), "#"))) AS ?stem)
    BIND(IRI(CONCAT(?stem, ".below")) AS ?below)
    BIND(IRI(CONCAT(?stem, ".inside")) AS ?inside)
    BIND(IRI(CONCAT(?stem, ".above")) AS ?above)
    BIND(CONCAT(STRAFTER(STR(?property), "#"), " of ", STRAFTER(STR(?subject), "#"), " below ", STR(?low)) AS ?belowLabel)
    BIND(CONCAT(STRAFTER(STR(?property), "#"), " of ", STRAFTER(STR(?subject), "#"), " inside ", STR(?low), "-", STR(?high)) AS ?insideLabel)
    BIND(CONCAT(STRAFTER(STR(?property), "#"), " of ", STRAFTER(STR(?subject), "#"), " above ", STR(?high)) AS ?aboveLabel)
} ;

#  And past the ENVELOPE: below the survival floor, above the survival ceiling — each also a
#  member of the region band it lies in, by the families' own subclass axioms.
INSERT { GRAPH $derived {
    ?belowFloor a owl:Class ; rdfs:subClassOf sensing:BelowFloor ; rdfs:label ?floorLabel ;
        owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( sosa:Observation
            [ a owl:Restriction ; owl:onProperty sosa:hasFeatureOfInterest ; owl:hasValue ?subject ]
            [ a owl:Restriction ; owl:onProperty sosa:observedProperty ; owl:hasValue ?property ]
            [ a owl:Restriction ; owl:onProperty sosa:hasSimpleResult ;
              owl:someValuesFrom [ a rdfs:Datatype ; owl:onDatatype xsd:decimal ;
                                   owl:withRestrictions ( [ xsd:maxExclusive ?floor ] ) ] ] ) ] .
    ?aboveCeiling a owl:Class ; rdfs:subClassOf sensing:AboveCeiling ; rdfs:label ?ceilingLabel ;
        owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( sosa:Observation
            [ a owl:Restriction ; owl:onProperty sosa:hasFeatureOfInterest ; owl:hasValue ?subject ]
            [ a owl:Restriction ; owl:onProperty sosa:observedProperty ; owl:hasValue ?property ]
            [ a owl:Restriction ; owl:onProperty sosa:hasSimpleResult ;
              owl:someValuesFrom [ a rdfs:Datatype ; owl:onDatatype xsd:decimal ;
                                   owl:withRestrictions ( [ xsd:minExclusive ?ceiling ] ) ] ] ) ] . } }
$given
WHERE {
    { SELECT ?property ?subject (MAX(?least) AS ?floor) (MIN(?most) AS ?ceiling) WHERE {
        ?subject ssn-system:hasOperatingRange/ssn-system:inCondition ?need .
        ?need ssn:forProperty ?property .
        { ?subject ssn-system:hasSurvivalRange ?envelope }
        UNION
        { ?instrument sensing:monitors ?subject ; ssn-system:hasSurvivalRange ?envelope }
        ?envelope ssn-system:inCondition ?tolerated .
        ?tolerated ssn:forProperty ?property ; schema:minValue ?least ; schema:maxValue ?most .
      } GROUP BY ?property ?subject }
    BIND(CONCAT("http://example.org/orexis#band.", ENCODE_FOR_URI(STRAFTER(STR(?subject), "#")), ".",
                ENCODE_FOR_URI(STRAFTER(STR(?property), "#"))) AS ?stem)
    BIND(IRI(CONCAT(?stem, ".belowFloor")) AS ?belowFloor)
    BIND(IRI(CONCAT(?stem, ".aboveCeiling")) AS ?aboveCeiling)
    BIND(CONCAT(STRAFTER(STR(?property), "#"), " of ", STRAFTER(STR(?subject), "#"), " below the floor ", STR(?floor)) AS ?floorLabel)
    BIND(CONCAT(STRAFTER(STR(?property), "#"), " of ", STRAFTER(STR(?subject), "#"), " above the ceiling ", STR(?ceiling)) AS ?ceilingLabel)
}

