"""The sensing layer of Agent 0.2.0: the translation row of the agent stack, and nothing above it.

**A TRANSPORT HANDS IT BYTES, AND IT MAKES OBSERVATIONS AND PREDICTIONS OF THEM.** `received`
is the callback a transport calls with the bytes it read for a sensor it owns: the pipeline —
codec, pointer, scaling — makes a number of them, and one `sosa:Observation` is written into
the graph of that key, holding from its instant to the horizon. `surprise` says whether the
number contradicted what was predicted for its instant, bound by bound against the ranges the
subject states. `predict` runs the domain's drifts over the observation and writes one
prediction per stretch between the instants the reading changes range — the crossing found
on numbers, by bisection against SSN-System's bounds. Everything is SOSA's and SSN's words and
the sensing package's, and not one word of any transport: what a sensor is wired to and what
its bytes mean is `wiring`, and how a device is reached is a driver's, behind the contract in
`driver.py`.

**IT CONCLUDES NOTHING.** Which side of a range an observation is on is a revision: the rules
this layer registers (`rules.ttl`, `register`) conclude it, and the deliberator runs them when
the container says a graph changed. No side, no want, no wake is written here. A range is
SSN-System's concept and so this layer's to read — for the crossing and the surprise — while
the side as a fact the mind reads is the rules'.

The 0.1.0 predecessor was a module that kept the pipeline, the predictions, a freshness desire
of its own, a timer per reading and the keeper's verdicts, and named the transport in its own
query; the pipeline and the drift runner are what came across, as functions.
"""
