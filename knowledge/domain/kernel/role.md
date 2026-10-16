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
so it lives with the agent's [stances](/domain/kernel/stance.md) and is read off the self graph alone,
before anything else the agent will run is. A fact a peer needs in order to address the agent is a
different thing: a relation the world states publicly, as `market:hosts` says which agent to call
about a venue. A role over something carries what it is over: an [observer](/domain/sensing/observer.md)
the sensors it reads. The market's roles still keep the relation they were founded on beside them,
until they carry their venue too.

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
