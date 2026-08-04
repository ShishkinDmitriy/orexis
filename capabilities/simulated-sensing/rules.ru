# Derivation: an agent that MODELS a subject perceives it by simulation.
#
# Keyed on ag:models, a property that exists only in this ontology — so no production wiring
# can grant this capability, and this wiring cannot grant a production one. The two never meet,
# which is the whole reason simulation is a separate package rather than a flag.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT { GRAPH <http://example.org/agora/graph/world> {
    ?agent ag:hasCapability ag:SimulatedSensing } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> { ?agent ag:models ?subject . ?subject a ?type }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:ModelledSubject }
}
