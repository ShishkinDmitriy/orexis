---
type: Domain Concept
title: Stance
description: >-
  A figure the agent holds about itself - how long it waits, how much a search or a revision may
  spend, how many cadences before it doubts a sensor, how far ahead it looks. A triple about the
  self in its self graph, declared by the package that reads it, read there alone, and the
  package's constant where nothing is stated. A belief, never configuration.
---

# What it is

A **stance** is one triple whose subject is the [self](/domain/kernel/self.md), authored in the
agent's self graph beside the row saying who it is:

```turtle
<> a orexis:SelfGraph .
:rose_grower a orexis:Self ;
    execution:patienceS 120 ;     # a step may go two minutes unanswered past its landing
    sensing:stuckAfter 3 .        # three unchanged cadences and a sensor is doubted
```

The word is the figure's, not the triple's: `execution:patienceS` is a stance whether or not a
world states it, and where none does the package reading it uses its own constant. That constant
is what holds when the agent said nothing about itself — never a second place the figure lives,
and never overridden by environment, a flag or a file beside the documents.

# The stances there are

Each is declared by the package that reads it, in its own `ontology.ttl`, with domain
`orexis:Self`, and read through the kernel's one reader, `stance` in `agent/stance.py`:

| term | what it bounds | read by | where none is stated |
|---|---|---|---|
| `execution:patienceS` | how long a commitment absorbs a second plan for its want, and how long past its latest landing a step may go unanswered | the [executor](/domain/execution/executor.md), when it is made | `DEFAULT_PATIENCE_S`, sixty seconds |
| `planning:budget` | candidates one want's search may weigh in a pass | the [planner](/domain/planning/planner.md), when it is made | `BUDGET` in `agent/planning/planner.py`, 32 |
| `belief:budget` | rule executions one pass of revision may spend | the [deliberator](/domain/belief/deliberator.md), when it is made | `BUDGET` in `agent/belief/deliberator.py`, 256 |
| `sensing:silentAfter` | cadences a reading may be missing before its sensor is said silent | `missed`, each pass | `SILENT_AFTER`, 3 |
| `sensing:stuckAfter` | cadences a number may stay the same before its sensor is said [stuck](/domain/sensing/stuck.md) | `received`, each reading | `STUCK_AFTER`, 6 |
| `prediction:horizonS` | seconds past an observation the drifts are accumulated | `predict`, each observation | `HORIZON_S`, a day |

What the two budgets are, in their units, is the [budget](/domain/planning/budget.md) page's.

# Read in the self graph, and nowhere else

The reader asks `?me a orexis:Self ; <term> ?n` over the graphs of kind `orexis:SelfGraph` alone. A
world graph saying `:rose_grower sensing:stuckAfter 3` states something about the agent in public —
which a peer may read and the agent may believe — and is not the agent's word about itself, so no
package reads it as one; nor is a figure in a graph of the agent's desires, or in a document a peer
sent. Nothing refuses such a triple: the loader holds no vocabulary to tell a stance from any other
fact about an agent, and a figure of an agent in a public graph may mean something to whoever reads
it.

One figure, stated once and as a number, is the stance. Two of one term, or one that is no number,
is the constant, said in the log; two answers are never picked between.

# What is not one

A figure is a stance only where it is the agent's word about ITSELF and a plan would branch on it
([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).
The grace a reading keeps past its due (`GRACE` in `agent/sensing/received.py`) is how late an
instrument's bytes may arrive — the sensor's and the path's, written into what an
[observation](/domain/sensing/observation.md) is, and stated of the sensor if it ever varies. How
often the metrics window is written is the admins' instrumentation, environment like the rest of a
[series](/domain/kernel/series.md). How a pass's revision budget is shared between sources, how
long a rate is held, how far a key no drift moves is carried: how the package does its work, not
how much the agent allows it.

Why a stance is a belief stated in the self graph rather than a flag, a file, a public graph or a
kind of its own:
[a-stance-is-the-agents-word-about-itself](/decisions/a-stance-is-the-agents-word-about-itself.md).
