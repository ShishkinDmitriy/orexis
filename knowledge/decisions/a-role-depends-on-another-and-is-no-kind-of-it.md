---
type: Decision
title: A role depends on the roles it works only beside, and is no kind of them
description: >-
  The sovereign, 2026-11-16 - `coordination:Coordinator rdfs:subClassOf planning:Planner` is wrong: a
  coordinator needs a planner running beside it and is not one. Four package roles and two of the market's were
  beneath the roles they need, so one class said both what a role is and what runs beside it, and a package
  deciding whether it runs read every other package's ontology for the classes beneath its own. Decided - a role
  class `orexis:dependsOn` the role classes its package works only beside, stated by whoever owns the words; an
  agent plays every role its roles depend on, each in its self graph with what it says; onboarding refuses one
  missing, once for every package and domain; and a package decides by its own class alone. Refused - subclassing
  one role beneath another for what it needs, a dependency that runs the depended-on package for the self, and a
  per-package shape for each need. Amends a-role-is-an-instance-an-agent-plays.
status: accepted
timestamp: 2026-11-16T12:00:00Z
---

# Context

A role class beneath another is a kind of it: everything true of a planner is true of whatever is beneath one.
The role classes had used it for something else. `coordination:Coordinator` was beneath the speaker, the planner
and the executor because a coordinator's draw is taken part in by committing and revealing, actions planning plans
and execution takes, and asking a peer is saying something; `sensing:Observer` was beneath the deliberator because
sensing's rules are run by belief; `translation:Translator` beneath the speaker; the market's host and bidder
beneath all four. None of them IS what it was beneath: a coordinator searches for no plan, and what holds of
every planner, a budget it searches within, is not said of it but of the planner running beside it. The lane's
couriers stated `planning:budget 256` on their coordinator role, a planner's figure on a role that plans nothing.

And the class hierarchy was what a package decided by. `Handed::plays` asks whether the self plays a role of the
package's class or of one beneath it, so planning, to know it runs on a lane courier, had to hold coordination's
ontology, where `Coordinator rdfs:subClassOf planning:Planner` was stated. That is why every package's documents
were put in the store before any start decided, and it is what stood in the way of a package bringing its own
documents as it starts (package).

# The decision

**A role depends on another where its package works only beside the other's, and it is no kind of it.**

```turtle
coordination:Coordinator rdfs:subClassOf orexis:Role ;
    orexis:dependsOn speech:Speaker , planning:Planner , execution:Executor .
```

- **`orexis:dependsOn`**, the kernel's, between role classes. It says nothing a reasoner concludes, and it is
  read by nobody at run time: it is what onboarding holds a self graph to.
- **Stated by whoever owns the words it is stated in**, as a role's need of the world already was: the
  coordinator's in coordination's ontology, the observer's of the deliberator in sensing's, the executor's of the
  planner in planning's, since execution speaks none of planning's words.
- **The agent plays every role its roles depend on**, each in its self graph, carrying what that role says: a
  lane courier plays a coordinator, a planner with its budget, an executor, a speaker, an observer and a
  deliberator. Onboarding refuses a role played without one it depends on, with one shape of its own for every
  package and domain (`onboarding/requirements.ttl`), where planning had shipped a SPARQL shape for the
  executor's need alone.
- **A package decides by its own class alone.** A domain's role classes beneath a package's still make a package
  run, a kind of it being one; no package role is beneath another package's.

# What was refused

- **A role beneath what it needs.** What was there, refused for saying two things with one relation: a
  coordinator would be a planner wherever a reader asked what a planner is, and a figure of the planner's was
  said on it.
- **A dependency that runs the depended-on package for the self.** The self playing a coordinator would then run
  planning without saying so: an author writes one role and three packages run. It is the subclass's closure under
  another name, and a package deciding by it reads the dependent package's ontology again.
- **A shape per need, shipped by each package.** The executor's need of a planner was one; a need between two
  roles is the same check whoever states it, so it is one relation and one shape.

# Consequences

- Six self graphs of shipped worlds and two of a test world state the roles their roles depend on, the lane's
  budget moving onto its planner.
- **A package may bring its own documents as it starts**, deciding first by its own class and waiting only on
  the packages its role depends on: the seam this opens, not yet built.
