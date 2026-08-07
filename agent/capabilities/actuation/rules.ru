# Derivation: you can actuate exactly what you own.
#
# Actuation is the power to touch the physical world, so it is never declared — it falls out
# of holding the hardware. A plant agent wins vouchers and still cannot open a valve, because
# it owns none.
#
# Note the two graphs: the WORLD says what type a device is, the T-BOX says what that type is
# a kind of. So a rule written against ag:Actuator picks up an ag:Valve without naming it, and
# a new kind of actuator works the day its class is declared.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT { GRAPH <http://example.org/agora/graph/world> { ?agent ag:hasCapability ag:Actuation } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> { ?agent ag:hasActuator ?device . ?device a ?type }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:Actuator }
}
