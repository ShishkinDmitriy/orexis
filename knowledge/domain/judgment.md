---
type: Domain Concept
title: Judgment
description: >-
  What one desire reads at one instant, and how badly it is wanted. Two halves. The met
  half is what the desire's own met-test read - met, or unmet with the results that say
  which instances fail and why - judged at the present and at every foreseen instant and
  written to the agent's judgment graph, whole, on every run of `judge_desires`; the wants
  are derived from that graph and nothing in hand. The urgency half a capability makes fresh
  on every pass - the ledger from a claim's redeem window, sensing from the survival
  envelope - and hands back unit-free, with what the thing currently reads and when it runs
  out. It is the mind's VIEW of a desire, never the desire.
term: http://example.org/orexis/deliberation#Judgment
---

# What it is

A desire says what this agent stands for and a [want](/domain/desire.md) says what it is
pursuing under one. Neither says how much it matters at this instant, and something has to, or
a litre owed and a pot drying cannot be ranked against each other. That answer is a judgment.

It carries the desire's name, an **urgency** between content and the edge of what can be borne,
what the thing currently reads where anybody has a number for it, and the instant it stops
being satisfiable. `Agent.pursuing()` hands back every one this agent is making, hottest first.

# The met half is written, the urgency half is not

A desire is a node in the roots graph and a want is a graph of its own with a period; both
survive a restart. A judgment exists for one run. Its MET half — what the desire's met-test
read, and the results where unmet, in SHACL's own words for a report, `sh:conforms` and
`sh:result` — is written to the agent's judgment graph by `judge_desires`, one judgment per
desire per instant, the present and every foreseen one, and the graph is replaced whole on
the next run. That is what makes the road two functions over the store
([judge-desires-then-derive-wants](/decisions/judge-desires-then-derive-wants.md)): the
wants are derived from the judgments and nothing in hand, and the judgments are there for
eyes, for the snapshots and for `orexis-ask` to answer *why do I want this*. The graph is a
WORKING one, like the deliberation trace: a conclusion, never carried into a possible world
and never a record, kept because a reader outside the process cannot recompute it.

The URGENCY half is still made fresh on every pass and written nowhere. Ask twice and you get
two, made from whatever the world looked like each time — which is correct, because urgency
is a function of a situation and a situation moves. The term `deliberation:Judgment` is the
written half's; the urgency joins it when the choir's answer is written beside it.

# The measure is the package's, the scale is the kernel's

Who makes the judgment is whoever holds the stake, and each does it its own way: a debt's
urgency comes from how much of its redeem window is left, a region's from how much room the
subject has before it ends, a call's is flat because a call is either open or not. The kernel
supplies no formula and could not — it does not know what a fern needs.

What the kernel supplies is that the number is **unit-free on every side**, which is what makes
the answers comparable without either contributor learning how the other computed its own. That
is the same discipline [urgency](/domain/urgency.md) states and the reason
[an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md)
could put the two kinds in one type: what differs is where the number came from, and that is in
the graph rather than in a flag anyone branches on.

# Why the word had to exist

For most of this project's life the class was called `Desire`, and it was doing both jobs — the
declared row and the per-pass answer. The two were told apart only by which file you were in,
and a collection of desires could not be built without deciding which of them it held. Naming
the second thing is what let the first become data. See
[a-desire-is-declared-and-a-judgment-is-made](/decisions/a-desire-is-declared-and-a-judgment-is-made.md).
