# Derivation: perception capabilities follow from the HARDWARE, not from an opinion.
#
# The sovereign states the wiring (which sensor an agent is on) and the device's own nature
# (does it answer on request, or announce on its own clock?). What the agent can therefore DO
# is computed from that. Change a board's firmware from push to pull, re-run genesis, and the
# agent gains a cadence — with no edit to any agent's declaration, because there is none to
# edit. The two can never drift apart, which is the whole point.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  A device that answers on request -> its agent DRIVES it.
INSERT { GRAPH <http://example.org/agora/graph/world> { ?agent ag:hasCapability ag:Polling } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> { ?agent ag:polls ?sensor . ?sensor a ?type ; ag:senseMode ag:Pull }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:Sensor }
} ;

#  A device that announces on its own clock -> its agent can only RECEIVE. It gets the
#  weaker capability, and its shapes will not ask it for a cadence it cannot apply.
INSERT { GRAPH <http://example.org/agora/graph/world> { ?agent ag:hasCapability ag:Listening } }
WHERE  {
    GRAPH <http://example.org/agora/graph/world> { ?agent ag:polls ?sensor . ?sensor a ?type ; ag:senseMode ag:Push }
    GRAPH <http://example.org/agora/graph/ontology> { ?type rdfs:subClassOf* ag:Sensor }
}
