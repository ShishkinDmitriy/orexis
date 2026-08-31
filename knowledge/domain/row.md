---
type: Domain Concept
title: Row
term: http://example.org/orexis#Row
description: >-
  One of three cognitive layers, told apart by how long a piece of work may take and whether it
  may be interrupted — reactive, progression, deliberative. A property of the QUESTION a module
  answers, declared on the hook itself, because one module answers in several rows and no
  directory can express that.
---

# The three

| row | how long | may it be interrupted | may it search |
|---|---|---|---|
| `orexis:Reactive` | milliseconds | no — it runs to the end | never |
| `orexis:Progression` | seconds to minutes | it suspends and is resumed | never |
| `orexis:Deliberative` | seconds | it should be | that is what it is for |

**Reactive** is classifying and writing: decode a payload, take a bid into a round, note a
device's word. **Progression** is carrying out what is already committed — an
[intention](/domain/intention.md) standing until the world answers, an [actor](/domain/actor.md)
that cannot act yet saying so. **Deliberative** is the search, and the only row a model may be
asked in.

# It is a property of a hook, not of a file

Every [choir](/domain/choir.md) hook declares its row (`orexis:row`). That is where it belongs
because a single module answers in several: sensing decodes a payload (reactive), nudges a probe
for a committed look (progression) and measures a want (deliberative) — three rows, one class,
so no arrangement of directories could say it. A term can also be checked, and is: a reactive
hook that reaches the planner fails a gate.

# The rule it exists to state

Anything that blocks belongs in progression, anything that searches belongs in deliberation,
anything that must never block belongs in the reactive row. Most architectural mistakes are one
piece of work sitting in the wrong one — a handler that calls a model, an act that spins waiting
for a value instead of standing. The argument is
[layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)'s.
