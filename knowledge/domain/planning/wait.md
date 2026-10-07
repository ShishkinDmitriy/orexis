---
type: Domain Concept
title: Wait
description: >-
  The search's own move - `planning:Wait`, the one action the planning package ships, which every
  agent loads and no world imports. It does nothing; it lands at the next ground whose identity
  differs from its own, so a plan can let the predictions move the world rather than act on it.
---

# What it is

The agent choosing to do nothing while what it foresees comes about: a van standing a cell short
while a peer's van crosses ahead, a grower letting the forecast rain fill the butt before watering.
Every world has it, so it belongs to no domain. It is an [action](/domain/kernel/action.md) like any other, a node in
`agent/planning/wait.ttl`, an `orexis:ActionGraph` the planning package keeps beside its ontology
and every agent reads at boot as it reads the package's other documents, and the node states its
cost and nothing else: no precondition, no effect, no landing, no implementation. Each absence is
read by the kernel for this one node. The page binds no `term:`, since the wait is an individual
declared in a graph of actions and the term gate reads ontologies alone.

# Where it lands

At the start of the next ground: the [prediction](/domain/prediction/prediction.md) lays one ground
per stretch in which nothing predicted changes, and a world stands in the one holding at its start.
The ground a wait reaches is the next one whose IDENTITY differs from the ground its world stands
in. A ground is a world — the present with the predictions applied, holding over the period in which
none of them changes — and a world's identity is its hash within what is read
([cone](/domain/planning/cone.md)). A later ground that differs only by a reading's number inside its
band is a ground of its own but the same place to the search, and a wait landing there would reach
the world it left, so `agent/planning/next_ground.py` walks the grounds and returns the first whose
identity differs. It coins nothing: merging such grounds into one was tried and refused, since a
ground's boundaries are also read as instants — where a want holds, where it is reached — and the
foreseen crossing of #858 read reached before its instant. So a single wait spans every stretch in which nothing
read is predicted to change, and no wait is offered at all where nothing is.

It lands at an INSTANT, not after a band: a path that reached its parent early waits the longer, and
the world it makes holds from that instant to the later of it and its parent's latest. That world
is the later ground with every step of the path replayed there, as any step landing in a later
ground is forked ([a-landing-is-a-band-and-a-world-holds-over-a-period](/decisions/a-landing-is-a-band-and-a-world-holds-over-a-period.md));
what the predictions moved in between is all it reaches.

# Why it is a move

A candidate whose effect comes to nothing is no move, and the search passes it over as a repeat of
the world it was taken in. The wait has no effect and is a move all the same, because `take` reads
the action it fills and forks it into the later ground; any other action whose rules change nothing
stays no move wherever it lands. So the one way a plan lets time pass is this declared node, and an
effect that happens to do nothing never becomes one.

# Where it is admitted

In every [scope](/domain/planning/scope.md): it touches no atom, so the partition would place it in
none, and `scope_actions` writes it into each. A scope's world admits it where `next_ground` finds
a ground ahead, filled with nothing — one candidate per world at most.

# What it costs

What its `planning:costs` select answers over the world it is taken in, as for any action: a tenth,
against the one every shipped act costs. More than nothing, so a plan is never padded with a wait
that buys nothing; less than an act, so standing still wins where it meets the want as well as
acting would — the refilled tank is met by waiting, and the rain that fills an empty butt is waited
for before the tank is filled (`agent/planning/tests/test_wait.py`). The figure is the same however
long the wait and whoever is waiting: what a path spent is written on the world's own row, which
every want of the scope shares, so no want can yet say that waiting is dear to it.

# What its step predicts

Nothing. Its [step](/domain/execution/step.md) names two graphs, both empty, since the effect changed
nothing in the ground it was replayed into — the refill or the other van's move is not its to
predict. The executor holds it to its `execution:landsAt` and answers it there, and taking it sends
nothing, there being no operation to run. Measured on the dispatcher with a peer's route laid ahead
and on the shipped worlds, in [measure-the-search](/runbooks/measure-the-search.md).
