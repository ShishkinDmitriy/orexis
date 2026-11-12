---
type: Domain Concept
title: Part
description: >-
  What a package contributes to a running agent - the package's own object, held by the one task the package
  spawns as it starts itself on the runtime. The planning package's part holds its Planner, execution's its executor,
  belief's its deliberator; a transport member is its own part. Made only where a role the agent is declared in
  calls for the package.
---

# Made, started, stopped

A part is made for every [package](/domain/kernel/package.md) the agent loads that has a `create`
module — each a declared [role](/domain/kernel/role.md) calls for — and the package **starts itself**
with it on the [runtime](/domain/kernel/runtime.md) (`create::start`): it takes a wait, says on it
what ends it — the timers it asks for, the kinds of graph written it hears, the trigger classes whose
events it hears ([policy](/domain/kernel/policy.md)) — takes the runtime's watch as where it says its
[events](/domain/kernel/event.md), and spawns its task. The runtime keeps the name each started under
(`runtime.parts`) and knows nothing else of them.

**The task's loop is the package's own.** It awaits its wait (`Wait::next`), is answered what woke it —
an event said, a graph written, an arrival, or a timer due — with the pass it is handled in, does what
its policy says of it, says which graphs it wrote (`Pass::done`), and waits again. No part is linked
to another: each is woken by what triggers it, and what one says another hears beneath its trigger,
reading what it names from the store. When the run ends the wait answers nothing, and the part stops itself.

What a part holds is its package's own object — the Planner, the executor, the deliberator — and the
events it says are that object's; the part only starts it
([a-package-starts-itself](/decisions/a-package-starts-itself.md)).
