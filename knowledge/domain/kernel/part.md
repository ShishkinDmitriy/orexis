---
type: Domain Concept
title: Part
description: >-
  What a package contributes to a running agent - it registers itself on the runtime, saying what it
  waits for, and its task is its own loop, which waits on its seat, decides, and stops itself when
  the run is over. The planning package's part holds its Planner, execution's its executor, belief's
  its deliberator; a transport member is its own part. Made only where a role the agent is declared
  in calls for the package.
---

# Its life, in three phases

A part is made for every [package](/domain/kernel/package.md) the agent loads that has a `create`
module — each a declared [role](/domain/kernel/role.md) calls for — and **registers itself** on the
[runtime](/domain/kernel/runtime.md) (`registers`), in the order a pass runs them, belief first and
the planner before the executor; the runtime keeps their names (`runtime.parts`) and knows nothing
else of them. Registering, a part says what it waits for — the timers it asks for, the kinds of
graph written it hears, the trigger classes whose events it hears
([policy](/domain/kernel/policy.md)) and the watch it says its [events](/domain/kernel/event.md) to —
and hands the runtime its task.

**The task's loop is the package's own.** It waits on its **seat**, what the runtime hands a part's
task to wait on (`Seat::next`), which answers what woke it — a timer due, a graph written, an event
said, or an arrival — and the pass it is handled in; the part does what its policy says of it, says
which graphs it wrote (`Pass::done`), and waits again. When the run ends the seat answers nothing,
and the part stops itself, the last registered first. No part is linked to another: what one says,
another hears beneath its trigger, reading what it names from the store.

What a part holds is its package's own object — the Planner, the executor, the deliberator — and the
events it says are that object's; the part only starts it
([a-package-starts-itself](/decisions/a-package-starts-itself.md)).
