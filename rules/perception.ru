# Derivation: which perception capability an agent gets, from the DEVICE'S NATURE.
#
# One fact decides it — does the device answer on request, or announce on its own clock? That
# is a property of the hardware and its firmware, not of anyone's opinion, so an agent's
# ability can never drift from its equipment. Reflash a board from push to pull, re-run
# genesis, and the agent gains a cadence with no edit to the agent, because there is nothing
# about it to edit.
#
# Note what is NOT consulted: how the device is spoken to. A pull board on MQTT and one on a
# GPIO pin give their agent the same ability and the same decisions; only the driver differs.
# Whether a given binding is COMPLETE (a pull sensor on a bus needs a command channel) is a
# question for that transport's shapes, not for this rule.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  Answers on request -> the agent DRIVES it, and owns a cadence.
INSERT { GRAPH <http://example.org/agora/graph/world> {
    ?agent ag:hasCapability ag:Polling } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> {
        ?agent ag:polls ?sensor . ?sensor a ?type ; ag:senseMode ag:Pull .
    }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:Sensor }
} ;

#  Announces on its own clock -> the agent can only RECEIVE, and is never asked for a cadence.
INSERT { GRAPH <http://example.org/agora/graph/world> {
    ?agent ag:hasCapability ag:Listening } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> {
        ?agent ag:polls ?sensor . ?sensor a ?type ; ag:senseMode ag:Push .
    }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:Sensor }
}
