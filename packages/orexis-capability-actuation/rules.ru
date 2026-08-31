# Derivation: you can actuate exactly what you own.
#
# Actuation is the power to touch the physical world, so it is never declared — it falls out
# of holding the hardware. A plant agent wins claims and still cannot open a valve, because
# it owns none.

PREFIX actuation: <http://example.org/orexis/actuation#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX orexis:   <http://example.org/orexis#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  The WHERE reads what is GIVEN — the sovereign's world and what the vocabulary entails of it —
#  and never what another rule derived. `$given` becomes the `USING` clauses that merge those
#  — substituted by the loader, so no rule names a graph — and it is doing real work:
#  `?agent actuation:hasActuator ?device` is the world's and `?device a sosa:Actuator` may be entailed, so
#  the two live in different graphs and no single `GRAPH` clause could match both.
#
#  The answer goes to the DERIVED graph, apart from the world it was computed from, so that
#  "who put this here" is answerable by looking rather than by knowing. See
#  knowledge/decisions/who-put-the-fact-there.md.
INSERT { GRAPH $derived {
    ?agent orexis:hasCapability actuation:Actuation } }
$given
WHERE  { ?agent actuation:hasActuator ?device . ?device a sosa:Actuator }
