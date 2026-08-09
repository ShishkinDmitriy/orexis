# Derivation: which perception capability an agent gets, from the DEVICE'S NATURE.
#
# One fact decides it — WHO HOLDS THE CLOCK. Can the device be asked at any moment, does it
# take an interval and keep to it, or does it announce on its own? That is a property of the
# hardware and its firmware, not of anyone's opinion, so an agent's ability can never drift
# from its equipment. Reflash a board from push to scheduled, re-run genesis, and the agent
# gains an interval to state with no edit to the agent, because there is nothing about it to
# edit.
#
# ag:Pull -> ag:Polling is deliberately ABSENT. The vocabulary declares both, because there
# are three ways to hold a clock and the T-Box should say so; but no board here is always
# reachable, and granting a capability no module implements would only produce a startup
# warning. The rule is the last piece to add, not the first.
#
# Note what is NOT consulted: how the device is spoken to. A pull board on MQTT and one on a
# GPIO pin give their agent the same ability and the same decisions; only the driver differs.
# Whether a given binding is COMPLETE (a pull sensor on a bus needs a command channel) is a
# question for that transport's shapes, not for this rule.

PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  Both rules ask what a thing IS, literally — no `rdfs:subClassOf*` walk, because the
#  vocabulary's entailments are asserted before any rule runs (agora/inference.py). What they
#  cannot do is name one graph: `ag:polls` is the sovereign's and `a ag:Sensor` may be entailed,
#  so the two facts live apart and a single `GRAPH` clause would match neither pair. `USING`
#  merges what is GIVEN — asserted and entailed — and deliberately not what another rule derived.
#
#  The answers go to the DERIVED graph. See knowledge/decisions/who-put-the-fact-there.md.

#  Keeps to an interval it is given -> the agent STATES that interval.
INSERT { GRAPH <http://example.org/agora/graph/world/derived> {
    ?agent ag:hasCapability ag:Subscribing } }
USING <http://example.org/agora/graph/ontology>
USING <http://example.org/agora/graph/ontology/entailed>
USING <http://example.org/agora/graph/world>
USING <http://example.org/agora/graph/world/entailed>
WHERE  { ?agent ag:polls ?sensor . ?sensor a ag:Sensor ; ag:senseMode ag:Scheduled } ;

#  Announces on its own clock -> the agent can only RECEIVE, and is never asked for a cadence.
INSERT { GRAPH <http://example.org/agora/graph/world/derived> {
    ?agent ag:hasCapability ag:Listening } }
USING <http://example.org/agora/graph/ontology>
USING <http://example.org/agora/graph/ontology/entailed>
USING <http://example.org/agora/graph/world>
USING <http://example.org/agora/graph/world/entailed>
WHERE  { ?agent ag:polls ?sensor . ?sensor a ag:Sensor ; ag:senseMode ag:Push }
