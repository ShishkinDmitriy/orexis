---
type: Decision
title: A stance is the agent's word about itself, stated in its self graph and read there alone
status: accepted
timestamp: 2026-10-08
description: >-
  What an agent holds about itself - its patience, the search's and revision's budgets, how long a
  sensor may be silent or stuck, how far ahead it looks - was constants, one flag nothing passed,
  and two limits read off public knowledge. Each is now a stance, a triple about the self in its
  self graph, declared by the package that reads it, read through one kernel reader in that graph
  alone, the package's constant where none is stated. Refused - a public graph beside
  `orexis:actsFor`, a stances kind of its own, a flag or environment, refusal at the loader. The
  second half of #876.
---

# What was true (measured 2026-10-08, on main at 2c20aeec)

**One figure was declared and read by nothing.** `execution:patienceS`, domain `orexis:Agent`; the
executor's `patience_s` returned `DEFAULT_PATIENCE_S` and its docstring said the figure "should not
stay one", the read having gone with 0.1.0's picks.

**Two were read off public knowledge.** `sensing:silentAfter` and `sensing:stuckAfter`, settled on
2026-10-03 as stated "of the agent by its world, in a public graph as `orexis:actsFor` is", were read
by `cadence.limit_of` over the public graphs and the self graph together. No shipped world stated
either.

**One had a flag, and nothing passed it.** The planner's `BUDGET`, 32, could be overridden by the
runtime's `--budget`; no `compose.yaml` passes it, so every deployed agent searched at 32, while the
worlds' own tests size their searches at 64 (Hanoi), 128 (the courier), 256 (the tower, the
dispatcher) and 512 (the dispatcher's corridor). Revision's 256 and prediction's day had no way in
at all.

# The decision

**A figure an agent holds about itself is a stance: a triple whose subject is the
[self](/domain/kernel/self.md), in the agent's self graph** —
`:rose_grower execution:patienceS 120` beside `:rose_grower a orexis:Self`. Each package declares the
figures it reads in its own ontology, with domain `orexis:Self`, and reads them through one kernel
reader, `stance` in `agent/stance.py`, which asks `?me a orexis:Self ; $stance ?n` over the graphs of
kind `orexis:SelfGraph` and nothing else; the package's constant stands where none is stated. The
kernel names no package's figure and no package names another's. What each is, and what reads it,
is [stance](/domain/kernel/stance.md)'s.

**Domain `orexis:Self`, not `orexis:Agent`.** A stance is only ever read of the self; a domain of
every agent invites stating it of a peer, which is exactly what is not read. Where the self graph
is passed over — a store holding a whole world, as `orexis-compose` and the simulator read it —
there is no self and so no stance, which is right: nobody is speaking for themselves there.

**Read when the part is made, or per pass.** The executor, the planner and the deliberator read
theirs at construction, since the self graph is authored at birth, a lived-in volume reads the
agent's own documents once, and nothing revises a stance; sensing and prediction read theirs
through the pass's memo, as the limits were read before.

**The flag is gone.** `--budget` is no longer an argument of the agent's process. `Runtime`,
`Planner` and `Deliberator` still take a budget a caller hands them — a test sizing a search, as
`revise` and `search` take theirs per call — and the process's `main` hands none, so a running agent
spends what it states of itself. No shipped world states a stance yet, so every agent still runs its
packages' constants, the dispatcher's search at 32 among them: which figure a world states is that
world's change, held by its own tests, and not this one's.

**Per figure, by the test of [model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)
and by whose word it is:**

| figure | verdict | why |
|---|---|---|
| patience | stance | when a step is given up decides when a want is re-searched |
| the search's budget | stance | a search cut short publishes nothing this pass; sized per agent from a measured cost |
| revision's budget | stance | a revision cut short leaves a side unconcluded that a met-test reads this pass |
| silent and stuck limits | stance | they decide when a row a met-test may read exists |
| horizon | stance | a crossing past it is not foreseen, so no want is minted for it and no plan made now |
| the grace a reading keeps | not one | how late an instrument's bytes arrive is the sensor's and the path's, written into the observation's period; stated of the sensor if it ever varies |
| the metrics window | not one | the admins' instrumentation; environment, like the rest of a series |

# What was refused

**Public knowledge beside `orexis:actsFor`** — the 2026-10-03 shape. Public means what every agent of
a world may read, and a figure there is the world's claim about an agent, which a peer may believe
of it. Read over the public graphs and the self graph together, a figure in either was the agent's,
so its word about itself had two homes and the world's could stand in for it silently.

**A graph kind of its own for stances**, beside the self graph. It would be a second private
document per agent saying who it is about — its own owner row, its own count at boot, its own door
at the loader — for a content the self graph already is: what the agent holds about itself. The
self graph's kind was made the kernel's for this (the-self-is-a-class-held-to-one-instance), and
#927's roles are to be stated there too.

**A flag, environment, or a file of figures.** Rule 5: there is no config file for the model. A
figure the agent believes about itself is a belief; a flag beside it is a second place the figure
lives, set by whoever writes the deployment rather than the sovereign who writes the world — and
the one flag there was showed what that costs, since nothing deploying an agent ever set it.

**Refusing a stance stated outside the self graph, at the loader.** The loader holds no vocabulary,
so it could tell a stance only by a marker on every such property — an `orexis:Stance` class read by
that refusal alone, which is annotation. And a world stating a figure of an agent in public is not
wrong, only not the agent speaking. It is not read; `agent/tests/test_stance.py` holds that a public
graph's figure and a desire graph's are not the self's.

# Seams left open

- **A stance is authored, and nothing revises it.** 0.1.0's review moved the agent's picks inside
  the room its world left ([self-review-is-a-capability](/decisions/0.1.0/self-review-is-a-capability.md));
  nothing here does, so a stance moves by an edit to the world and a fresh volume. The trigger is the
  first figure an agent would do better to move by itself — a budget exhausted pass after pass is the
  likeliest, and [reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md)
  proposes such an edit rather than making one.
- **A stance added to a lived-in volume's world is not read** until the volume is fresh — the self
  record's seam, unchanged.
- **A figure is not checked for sense.** A budget of nought or a negative patience is read as stated;
  what would catch it is a world's tests, as for any other figure a world states.
