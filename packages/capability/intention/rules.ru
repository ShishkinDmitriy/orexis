# Derivation: who keeps intentions — from a stake AND a lever.
#
# The premise is both halves and neither alone. A commitment is to reduce a named gap by a named
# means, so an agent with no stake has nothing to commit ABOUT (world/sensing's agent records,
# wants nothing, and commits to nothing), and an agent with no lever has nothing to commit TO —
# wanting without means is a wish, not an intention. The supplier fails the first half; a
# hypothetical agent acting for a plant it cannot look at, bid for or water would fail the
# second.
#
# The stake is restated from base facts rather than read as the desire capability's own
# conclusion, and must be: $given excludes every graph rules write into, so one rule can never
# read what another derived — otherwise the answer would depend on load order. The three levers are the three
# means the ontology names: a market position (Acquire), an actuator (Apply, reserved), and a
# schedulable sensor (Observe — a board that can be ASKED to look; a push board looks on its own
# clock and offers nothing to commit to).

PREFIX intention: <http://example.org/agora/intention#>
PREFIX sensing: <http://example.org/agora/sensing#>
PREFIX actuation: <http://example.org/agora/actuation#>
PREFIX market: <http://example.org/agora/market#>
PREFIX ag:   <http://example.org/agora#>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>

INSERT { GRAPH $derived {
    ?agent ag:hasCapability intention:Keeping } }
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
