---
type: Domain Concept
title: Part
description: >-
  What a package contributes to a running agent - the package's core, one struct named for the role the package is
  loaded for and read off it, made and held by the one task that is the package running. Planning's part is its
  Planner, execution's its executor, belief's its deliberator; a transport member's part holds the member. Made only
  where a role the agent is declared in calls for the package, and nothing outside its task holds it.
---

# Made, held, stopped

A part is made for every [package](/domain/kernel/package.md) the agent loads — each a declared
[role](/domain/kernel/role.md) calls for — by the package's own start, which whoever runs the agent calls and
knows nothing more of (`orexis::task::Package`). The start makes the part from the store it is handed, says what
its task hears, the trigger classes whose [events](/domain/kernel/event.md) wake it
([policy](/domain/kernel/policy.md)) and the kinds of graph written, and goes on as that task.

**The part is the role's struct.** Its `new` reads the role the self plays off the store, a field for each thing
the role may say, and the same struct keeps what the package carries from one turn to the next and does what its
policy asks: the `Deliberator`, the `Coordinator`, the `Executor`, the `Planner`, the `Observer`, the `Speaker`,
the `Translator`, the `Meter`, the `Predictor`, each in a file of the crate named for it. A second struct beside the
role's - `Sensing` beside the `Observer`, `Execution` around the `Executor`, `Coordination` beside the
`Coordinator` - was what this replaced: two names for one thing the package runs. A transport plays no role, and its part holds the member.

**The task is the package running, and the part is its alone.** It awaits what it hears, an arrival
from outside, or the clock; takes a **turn** — what a task does of one thing that woke it, at the
instant the clock then reads (`Turn`) — in which it calls the part, says which graphs it wrote, and
may say when it is next due; and waits again. No part is linked to another and none is read from
outside: what one says another hears beneath its trigger, reading what it names from the store, and a
test of a running agent holds what was said and what the store holds. When the run ends the task
stops itself ([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[a-package-is-a-task-that-awaits-its-events](/decisions/a-package-is-a-task-that-awaits-its-events.md)).
