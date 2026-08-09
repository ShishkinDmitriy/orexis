# Derivation: you can actuate exactly what you own.
#
# Actuation is the power to touch the physical world, so it is never declared — it falls out
# of holding the hardware. A plant agent wins vouchers and still cannot open a valve, because
# it owns none.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  The WHERE reads what is GIVEN — the sovereign's world and what the vocabulary entails of it —
#  and never what another rule derived. `USING` is what merges those, and it is doing real work:
#  `?agent ag:hasActuator ?device` is the world's and `?device a ag:Actuator` may be entailed, so
#  the two live in different graphs and no single `GRAPH` clause could match both.
#
#  The answer goes to the DERIVED graph, apart from the world it was computed from, so that
#  "who put this here" is answerable by looking rather than by knowing. See
#  knowledge/decisions/who-put-the-fact-there.md.
INSERT { GRAPH <http://example.org/agora/graph/world/derived> {
    ?agent ag:hasCapability ag:Actuation } }
USING <http://example.org/agora/graph/ontology>
USING <http://example.org/agora/graph/ontology/entailed>
USING <http://example.org/agora/graph/world>
USING <http://example.org/agora/graph/world/entailed>
WHERE  { ?agent ag:hasActuator ?device . ?device a ag:Actuator }
