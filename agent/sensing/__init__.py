"""The sensing layer of Agent 0.2.0: the translation row of the agent stack, and nothing above it.

**A TRANSPORT HANDS IT BYTES, AND IT MAKES PERCEPTS OF THEM.** `received` is the callback a
transport calls with the bytes it read for a sensor it owns: the pipeline — codec and pointer —
makes a number of them, and one `sosa:Observation` per reading is written into a graph of its own,
a percept linked to the one before it, holding from its instant until the next is due by the
sensor's `ssn-system:Frequency` and a grace past it, or until the next arrives; a sensor's last
`sensing:stuckAfter` are kept, and no reader of the mind is handed one (#944).
`missed` is what sensing's own `start` asks every minute: which sensors' readings have gone missing with
nothing arrived, for the container to nudge, and which of them have been silent for a limit
of their cadences, said so by `sensing:silentSince` until a reading ends it. Everything is
SOSA's and SSN's words — a sensor `sosa:observes` a property and `sosa:isHostedBy` what it is
mounted in, and that pair is what an observation is of — but the words this layer declares in
`ontology.ttl`, and not one word of any transport: how a sensor's bytes decode is the pipeline's
binding on it, and how a device is reached is a transport's, whose contract is the transport
family's own and which hands `received` the sensor's IRI and bytes.

**IT PREDICTS NOTHING AND CONCLUDES NOTHING.** When the reading changes range is the prediction
package's calculation, over the latest percept written here. What a percept is of, its quantity,
and whether its sensor is stuck on one number are revisions: the rules this layer ships
(`rules.ttl`, a document saying it is a `sh:RulesGraph`, which a boot reads as it reads every
document) conclude them, and the deliberator runs them when sensing's part hands it a percept
written, saying the revision is of this layer's kind — the runner of belief's revision over its own
observations, since belief, beneath, knows no word of them (#944).
No state, no want, no wake is written here; a range is SSN-System's concept, read by a domain's
transitions and by the prediction package, minted by nobody.

The 0.1.0 predecessor was a module that kept the pipeline, the predictions, a freshness desire
of its own, a timer per reading and the keeper's verdicts, and named the transport in its own
query; the pipeline came across as functions, the predictions went to a package of their own,
and what remains of the timer is a read of the catalogue on somebody else's tick.
"""
