---
type: Domain Concept
title: Part
description: >-
  What a package contributes to a running agent - the package's own object, made and held by the one task that is
  the package running. The planning package's part holds its Planner, execution's its executor, belief's its
  deliberator; a transport member is its own part. Made only where a role the agent is declared in calls for the
  package, and nothing outside its task holds it.
---

# Made, held, stopped

A part is made for every [package](/domain/kernel/package.md) the agent loads that has a `create`
module — each a declared [role](/domain/kernel/role.md) calls for — by the package's own start, which
whoever runs the agent calls and knows nothing more of (`orexis::task::Package`). The start makes the
part from what it is handed — the store, the clock, the events, and what reaches outside — says what
its task hears, the trigger classes whose [events](/domain/kernel/event.md) wake it
([policy](/domain/kernel/policy.md)) and the kinds of graph written, and answers the task.

**The task is the package running, and the part is its alone.** It awaits what it hears, an arrival
from outside, or the clock; takes a **turn** — what a task does of one thing that woke it, at the
instant the clock then reads (`Turn`) — in which it calls the part, says which graphs it wrote, and
may say when it is next due; and waits again. No part is linked to another and none is read from
outside: what one says another hears beneath its trigger, reading what it names from the store, and a
test of a running agent holds what was said and what the store holds. When the run ends the task
stops itself.

What a part holds is its package's own object — the Planner, the executor, the deliberator — and the
events it says are that object's; the part only starts it
([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[a-package-is-a-task-that-awaits-its-events](/decisions/a-package-is-a-task-that-awaits-its-events.md)).
