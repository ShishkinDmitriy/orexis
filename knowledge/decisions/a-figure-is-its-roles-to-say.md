---
type: Decision
title: A figure a package runs by is its role's to say, and the self states none
status: accepted
timestamp: 2026-11-15T12:00:00Z
description: >-
  The sovereign's ruling of 2026-11-15. A package's figures lay in two places, the patience, the budgets and the
  horizon as triples about the self, a sensor's limits and every interval on the role. Each is now said on the role
  the package is loaded for, read by that package's own query, with the default its ontology states on the role's
  shape. Refused - keeping stances on the self beside the roles, a kernel reader of figures, and a default as a
  constant in code.
---

# What was decided

**A figure a package runs by is said on the role the package is loaded for, in the agent's self graph, and the
self states none of its own.** The planner's role says `planning:budget` and `planning:budgetEveryS`, the
executor's `execution:patienceS`, the coordinator's `coordination:patienceS`, `coordination:rounds` and
`coordination:lookahead`, the predictor's `prediction:horizonS`, the deliberator's `belief:budget`:

```turtle
:courier a orexis:Self ;
    orexis:plays [ a planning:Planner ; planning:budget 128 ] ,
                 [ a execution:Executor ; execution:patienceS 120 ] .
```

Each package reads its own, by a query it spells, and where no role says a figure the default its ontology states
holds, `sh:defaultValue` on its shape of the role. The kernel reads no figure for a package; what it keeps is the
reader of an ontology's defaults (`orexis/src/shape.rs`), which knows no role and no property. What a role is and
how a package reads one is [role](/domain/kernel/role.md)'s.

# Why

A role already carried figures: an observer's two limits since
[a-role-is-an-instance-an-agent-plays](/decisions/a-role-is-an-instance-an-agent-plays.md), and since the world
came to say what it is connected to, every interval and every link to a service
([the-world-says-what-it-is-connected-to](/decisions/the-world-says-what-it-is-connected-to.md)). So how a package
is configured was asked in two places by two readers, and an author had to know which figure went on the self and
which on the role. On the role, a package is one struct read from one node: what it may be told is the role's
properties, and an agent that does not play the role has nowhere to state the figure, where a stance could be
stated by an agent no package read it for.

# What was refused

**Stances kept on the self, beside the roles.**
[a-stance-is-the-agents-word-about-itself](/decisions/a-stance-is-the-agents-word-about-itself.md) put these
figures on the self as the agent's word about itself, and its argument against a public graph, a flag and the
environment stands: a figure is still authored in the self graph and read there alone. What falls is the subject.
The role is the agent's word about itself too, and it is the part of that word the package is loaded by.

**A kernel reader of figures.** The kernel's `stance` read any stance for any package, and a reader of roles
built after it handed every package what its roles say. Either is the kernel doing a package's reading; a package
that spells its own query can be read alone, and its struct is one to one with its role's class.

**A default as a constant in code.** Each figure had one, also written in its property's comment, so the number
lived twice and the document was not the source.

# Seams left open

- **A figure is authored, and nothing revises it**, as before: it moves by an edit to the world and a fresh
  volume, since a volume lived in keeps the agent's own graphs.
- **Nothing holds a figure to the class its property is declared for.** A package reads the figure off any role the
  self plays, so one said on the wrong role is still read. A requirement of onboarding's would refuse it, when a
  world gets it wrong.
- **`coordination:secret` stays on the self.** It is no figure a package runs by, but which lot the agent draws.
