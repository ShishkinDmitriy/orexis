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
them by package (`runtime.parts`), each handed the one watch every part says its
[events](/domain/kernel/event.md) to. Then `start` on each: the jobs it submits, the timers it asks for,
the kinds of graph written it hears and the trigger classes whose events it hears
([policy](/domain/kernel/policy.md)). `stop()`, the last first, when the run ends. No part is linked to
another: what one says, another hears beneath its trigger, reading what it names from the store.

What a part holds is its package's own object — the Planner, the executor, the deliberator — and the
events it says are that object's; the part only starts it
([a-package-starts-itself](/decisions/a-package-starts-itself.md)).
