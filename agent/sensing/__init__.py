"""The sensing layer of Agent 0.2.0: the translation row of the agent stack, and nothing above it.

**A TRANSPORT HANDS IT BYTES, AND IT MAKES OBSERVATIONS OF THEM.** `received` is the callback a
transport calls with the bytes it read for a sensor it owns: the pipeline — codec, pointer,
scaling — makes a number of them, and one `sosa:Observation` is written into the graph of that
key, holding from its instant until the next is due by the sensor's `ssn-system:Frequency`.
`missed` is what the container's tick calls: which sensors' readings have fallen due with
nothing arrived, for the container to nudge, and which of them have been silent for a limit
of their cadences, said so by `sensing:silentSince` until a reading ends it. Everything is
SOSA's and SSN's words — a sensor `sosa:observes` a property and `sosa:isHostedBy` what it is
mounted in, and that pair is the key an observation is written under — but the six this layer
declares in `ontology.ttl`, and not one word of any transport: how a sensor's bytes decode is
the pipeline's binding on it, and how a device is reached is a transport's, whose contract is
the transport family's own and which hands `received` the sensor's IRI and bytes.

**IT PREDICTS NOTHING AND CONCLUDES NOTHING.** When the reading changes range is the prediction
package's calculation, over the observation written here. Which side of a range an observation
is on is a revision: the rules this layer registers (`rules.ttl`, `register`) conclude it, and
the deliberator runs them when the container says a graph changed. No side, no want, no wake
is written here; a range is SSN-System's concept, read by the rules and by the prediction
package, minted by nobody.

The 0.1.0 predecessor was a module that kept the pipeline, the predictions, a freshness desire
of its own, a timer per reading and the keeper's verdicts, and named the transport in its own
query; the pipeline came across as functions, the predictions went to a package of their own,
and what remains of the timer is a read of the catalogue on somebody else's tick.
"""
