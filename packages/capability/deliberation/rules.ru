# Derivation: who deliberates — from a stake AND a lever, the same premise that grants keeping.
#
# The same premise DELIBERATELY, not coincidentally: deciding what to do about a gap and
# remembering what was decided are meaningful under exactly the same conditions — something to
# advance for, and some way to act on it. An agent with either half missing has nothing to
# decide; world/sensing's agent records, the supplier hosts, and neither arises here.
#
# They stay two capabilities despite the shared premise because they are different ABILITIES
# with different replaceable parts: how commitments are kept could change without changing how
# decisions are reached, and — the case this family exists for — the other way round. One rule
# each, in the package that owns the conclusion.
#
# deliberation:Consulting is deliberately ABSENT, exactly as desire's and review's are. What
# would SELECT between reflex and a model once both exist is an open seam — the rule is the
# last piece to add, not the first.

PREFIX deliberation: <http://example.org/agora/deliberation#>
PREFIX sensing: <http://example.org/agora/sensing#>
PREFIX actuation: <http://example.org/agora/actuation#>
PREFIX market: <http://example.org/agora/market#>
PREFIX ag:   <http://example.org/agora#>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>

INSERT { GRAPH $derived {
    ?agent ag:hasCapability deliberation:Reflex } }
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
