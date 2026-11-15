---
type: Domain Concept
title: Role
term: http://example.org/orexis#Role
description: >-
  What an agent runs and may do - an instance the agent plays, declared in its own self graph and
  never derived from the world, carrying its own context. A package declares the role classes it
  serves, a domain declares role classes in its own words beneath those, and only a package one of
  the agent's roles calls for is loaded. No role is every agent's.
---

# What it is

`orexis:Role` is the class every role class is beneath. A role is an INSTANCE the agent plays, never
its type: the agent says it `orexis:plays` it, beside `orexis:Self`, in its
[self graph](/domain/kernel/self.md), and the role carries what belongs to it there:

```turtle
:supplier a orexis:Self ; orexis:plays [ a market:Host ] .
:terrace_agent a orexis:Self ;
    orexis:plays [ a sensing:Observer ; sensing:sensor :moisture_sensor_terrace , :forecast_terrace ] ,
                 [ a prediction:Predictor ] .
```

A role is anonymous unless something must refer to it, holds over the period of the graph it is
stated in, and is of a role class, which is what the boot closes and loads packages by. Why an
instance and not a type — a context, more than one at once, a period — is
[a-role-is-an-instance-an-agent-plays](/decisions/a-role-is-an-instance-an-agent-plays.md).

It says what THIS agent runs. Nothing outside the agent reads it — not a peer, not the public world —
so it is read off the self graph alone,
before anything else the agent will run is. A fact a peer needs in order to address the agent is a
different thing: a relation the world states publicly, as `market:hosts` says which agent to call
about a venue. A role over something carries what it is over: an [observer](/domain/sensing/observer.md)
the sensors it reads. The market's roles still keep the relation they were founded on beside them,
until they carry their venue too. One role is stated in the world rather than the self graph, because
a peer finds the agent by it: the courier's [driver](/domain/courier/driver.md), which loads nothing.

# Who declares which

- **A package declares the roles it serves** — the [deliberator](/domain/belief/deliberator.md), the
  [observer](/domain/sensing/observer.md), the [predictor](/domain/prediction/predictor.md), the
  [planner](/domain/planning/planner.md), the [executor](/domain/execution/executor.md), the
  [speaker](/domain/speech/speaker.md). A role and the part that plays it are one concept, so each is
  the word its part already had where it had one; how declaring one loads its package is the
  [package](/domain/kernel/package.md)'s to say.
- **A domain declares roles in its own words, beneath package roles.** The market's
  [host](/domain/market/host.md) and [bidder](/domain/market/bidder.md) sit beneath the four package
  roles a market agent needs, so an author declares a host and never lists what a host runs.
- **An author declares a package role directly** where no domain has a word for what the agent is:
  Hanoi's mover is a planner and nothing else, its plan its output — and planning, finding no
  executor to link to, lets it go `planned` once the plan is published ([runtime](/domain/kernel/runtime.md)).

# How a package reads it

By itself. A package that takes anything from its role declares a struct named for the role's class, with a field
for each thing the role may say: a figure, a word, or where the service a link names answers, which the world's
derived [deployment](/domain/onboarding/deployment.md) states. The struct is made from the store
(`Recorder::new(store)`), by a query the package owns, and the kernel reads no role for a package. A figure the
role does not state is the default the package's ontology states on its shape of the role (`sh:defaultValue`), the
one place the figure lives, read off the store beside the role or off the ontology the package brings
(`orexis/src/shape.rs`), and a link it does not state is none. So what an author can tell a
package is the fields of one struct, one to one with the role's class: the journal's `Recorder`, `Observer` for
what archives sensing's readings, the metrics' `Meter`. Several roles of one class are read as one.

# The figures a role states

A figure a package runs by is said on the role it is loaded for, and the self states none of its own
([a-figure-is-its-roles-to-say](/decisions/a-figure-is-its-roles-to-say.md)):

```turtle
:rose_grower a orexis:Self ;
    orexis:plays [ a execution:Executor ; execution:patienceS 120 ] ,   # a step may go two minutes unanswered
                 [ a prediction:Predictor ; prediction:horizonS 43200 ] . # the flows are accumulated half a day
```

| term | on the role of | what it bounds | where none is stated |
|---|---|---|---|
| `execution:patienceS` | the [executor](/domain/execution/executor.md) | how long a commitment absorbs a second plan for its want, and how long past its latest landing a step may go unanswered | sixty seconds |
| `planning:budget` | the [planner](/domain/planning/planner.md) | candidates one want's search may weigh in one planning | 32 |
| `planning:budgetEveryS` | the planner | seconds a budget is for | ten seconds |
| `belief:budget` | the [deliberator](/domain/belief/deliberator.md) | rule executions one pass of revision may spend | 256 |
| `prediction:horizonS` | the [predictor](/domain/prediction/predictor.md) | seconds past an observation the flows are integrated | a day |
| `coordination:patienceS`, `rounds`, `lookahead` | the [coordinator](/domain/coordination/coordinator.md) | how long a draw stands undecided, how often it restarts, how many of a silent peer's steps are foreseen | sixty seconds, three, two |

The intervals a package takes its turn at and an observer's two limits are figures of their roles the same way,
each on its own page. A figure is read in the self graph and in no other: a world graph saying a figure of an
agent states something about it in public, which no package reads as the role's. One figure, said once and as a
number, is the figure; several, or one that is no number, is the default, said in the log. And a figure is a
role's only where a plan would branch on it or an author would choose it
([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)): the
grace a reading keeps past its due is the instrument's, and how a pass's revision budget is shared between
sources is how the package does its work.

# What it is held to

There is **no default**. An agent playing no role runs nothing and `orexis-onboard` refuses it — a
default would be a kind said by absence, and a role every agent has is not a role, since its holder
could not cease to hold it. Each role's needs of the world are a shape, shipped by whoever owns the
words the need is stated in, and [onboarding](/domain/onboarding/onboarding.md) holds a declaration
to its world both ways.

A role loads code; it does not narrow which steps an agent's actions admit, which stays their
preconditions' to say over public relations. And it is anti-rigid, though changing one on a running
agent is not built: the self graph is the agent's own, so a role added after birth reaches it only on
a fresh volume
([a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md)).
