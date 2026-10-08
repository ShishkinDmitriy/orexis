---
type: Domain Concept
title: Part
description: >-
  What a package contributes to a running agent - made by its create(runtime), linked to the other
  parts, started, and stopped last-first. The planning package's part holds its Planner, execution's
  its executor, belief's its deliberator; a transport member is its own part. Made only where a role
  the agent is declared in calls for the package.
---

# Its life, in three phases

The [runtime](/domain/kernel/runtime.md) makes a part for every [package](/domain/kernel/package.md)
the agent loads that has a `create` module — each a declared [role](/domain/kernel/role.md) calls
for — in the order a pass runs them, belief first and the planner before the executor, and keeps
them by package (`runtime.parts`). When all exist it calls `link(parts)` on each, so a part connects
its own [signals](/domain/kernel/signal.md) to what lies beneath it and hears theirs — nothing need
exist before anything else, which one phase of starting could not promise. Then `start(runtime)` on
each: the jobs it submits, the timers it asks for, the kinds of graph written it hears. `stop()`,
the last first, when the run ends. A part with nothing to link or to stop has no such method.

What a part holds is its package's own object — the Planner, the executor, the deliberator — and its
signals are that object's; the part only wires and starts it
([a-package-starts-itself](/decisions/a-package-starts-itself.md)).
