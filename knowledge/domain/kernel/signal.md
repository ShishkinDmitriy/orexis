---
type: Domain Concept
title: Signal
description: >-
  A package's own word for something that just happened - the Planner's plan_published, the
  executor's intention_resolved, the deliberator's revised - living on the package's object, emitted
  at once on the one thread to whatever was connected when the parts were linked. Never stored.
---

# What it is

A signal says that something happened, so that whoever is connected can act now: the Planner publishes
a plan and the executor adopts it; the executor ends an intention and planning plans again; the
deliberator revises the present and the executor walks. It is an attribute of the package's own object —
`planner.plan_published`, `executor.intention_resolved`, `deliberator.revised` — so the package that
says it owns the word, and the kernel holds only the mechanism (`agent/lifecycle.py`). Emitting one
calls every connected handler at once, on the runtime's one thread, and answers what they wrote.

Signals are connected when the [parts](/domain/kernel/part.md) are linked, and a connection points down
the stack as an import does: planning connects its Planner's signals to the executor, execution its
executor's to the transports and speech, and each hears the signals of what lies beneath it.

The runtime owns one of its own: a graph written, which a part hears by kind (`runtime.on`) — how
belief revises what is written and prediction answers an observation.

# What it is not

**A fact.** A signal is not stored. What happened is in the store — the plan, the intention's outcome,
the graph — and a handler reads it there, so a restart that replays no signal loses nothing. **A call
the emitter chose.** The emitter does not know who is connected, or whether anyone is
([a-package-starts-itself](/decisions/a-package-starts-itself.md)).
