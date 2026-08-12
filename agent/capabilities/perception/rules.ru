# Derivation: which perception capability an agent gets, from the DEVICE'S NATURE.
#
# One fact decides it — WHO HOLDS THE CLOCK. Can the device be asked at any moment, does it
# take an interval and keep to it, or does it announce on its own? That is a property of the
# hardware and its firmware, not of anyone's opinion, so an agent's ability can never drift
# from its equipment. Reflash a board from push to scheduled, re-run genesis, and the agent
# gains an interval to state with no edit to the agent, because there is nothing about it to
# edit.
#
# perception:PolledSampling -> perception:Polling is deliberately ABSENT. The vocabulary declares both, because there
# are three ways to hold a clock and the T-Box should say so; but no board here is always
# reachable, and granting a capability no module implements would only produce a startup
# warning. The rule is the last piece to add, not the first.
#
# Note what is NOT consulted: how the device is spoken to. A pull board on MQTT and one on a
# GPIO pin give their agent the same ability and the same decisions; only the driver differs.
# Whether a given binding is COMPLETE (a pull sensor on a bus needs a command channel) is a
# question for that transport's shapes, not for this rule.

PREFIX perception: <http://example.org/agora/perception#>
PREFIX unit: <http://qudt.org/vocab/unit/>
PREFIX schema: <https://schema.org/>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX review: <http://example.org/agora/review#>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX ag:   <http://example.org/agora#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

#  Both rules ask what a thing IS, literally — no `rdfs:subClassOf*` walk, because the
#  vocabulary's entailments are asserted before any rule runs (agora/inference.py). What they
#  cannot do is name one graph: `perception:polls` is the sovereign's and `a perception:Sensor` may be entailed,
#  so the two facts live apart and a single `GRAPH` clause would match neither pair. `$given`
#  becomes the `USING` clauses that merge what is GIVEN — asserted and entailed — and
#  deliberately not what another rule derived. `$derived` is where conclusions land. Both are
#  substituted by the loader: a graph IRI is an instance, and a rule should not name one.
#
#  The answers go to the DERIVED graph. See knowledge/decisions/who-put-the-fact-there.md.

#  Keeps to an interval it is given -> the agent STATES that interval.
INSERT { GRAPH $derived {
    ?agent ag:hasCapability perception:Subscribing } }
$given
WHERE  { ?agent perception:polls ?sensor . ?sensor a sosa:Sensor ; perception:senseMode perception:ScheduledSampling } ;

#  Announces on its own clock -> the agent can only RECEIVE, and is never asked for a cadence.
INSERT { GRAPH $derived {
    ?agent ag:hasCapability perception:Listening } }
$given
WHERE  { ?agent perception:polls ?sensor . ?sensor a sosa:Sensor ; perception:senseMode perception:PushReporting } ;

#  What the EQUIPMENT allows, carried from the sensor to the agent that polls it.
#
#  An agent cannot ask its sensors what they can do — `ranges()` narrows a belief it holds, and
#  a belief is the agent's, so the limit has to reach the agent as a fact ABOUT THE AGENT. This
#  is the carry: whatever floor any sensor an agent polls declares becomes a floor on that
#  agent's cadence, because an agent polling two devices can go no faster than its slowest.
#
#  `MAX`, and that is the whole of the arithmetic. Two sensors on one agent, one honouring 30s
#  and one 60s, leave the agent with 60: a floor is the tightest constraint that binds, and
#  taking the min would let the slower board be asked for something it will never keep — which
#  is the exact failure this exists to prevent, arrived at from the other side.
#
#  Shaped as a review:Commitment because it narrows the same term the same way and `ranges()`
#  can then intersect both with one arithmetic. Under review:limitedTo and never
#  review:commits: one is what a board can do and the other what a sovereign allowed, and a
#  refused revision should say which of the two refused it.
INSERT { GRAPH $derived {
    ?agent review:limitedTo [ review:onTerm perception:slowSleepS ; review:notBelow ?floor ] } }
$given
WHERE  {
    { SELECT ?agent (MAX(?s) AS ?floor) WHERE {
        ?agent perception:polls ?sensor .
        ?sensor ssn-system:hasSystemCapability ?cap .
        ?cap ssn-system:hasSystemProperty ?freq .
        ?freq a ssn-system:Frequency ; schema:value ?s ; schema:unitCode unit:SEC .
      } GROUP BY ?agent }
}
