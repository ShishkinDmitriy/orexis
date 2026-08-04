# Derivation: you can pretend to actuate exactly what you hold a pretend device for.
#
# Keyed on ag:hasSimulatedActuator and ag:SimulatedActuator, both of which exist only in this
# ontology — so the production rule (which matches ag:Actuator) cannot fire for these devices,
# and this rule cannot fire for real ones. The two capabilities are mutually exclusive by
# vocabulary rather than by a filter anyone could forget.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT { GRAPH <http://example.org/agora/graph/world> {
    ?agent ag:hasCapability ag:SimulatedActuation } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> {
        ?agent ag:hasSimulatedActuator ?device . ?device a ?type }
    GRAPH <http://example.org/agora/graph/ontology> {
        ?type rdfs:subClassOf* ag:SimulatedActuator }
}
