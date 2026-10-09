---
type: Service
title: Deliberator
term: http://example.org/orexis/belief#Deliberator
description: >-
  The belief package's pass - the D of BDI in its first sense, facts following from facts - and the
  role of an agent that runs it. A writer says a graph changed; the pass revises every changed graph
  in turn, within a budget of rule executions, and a graph the budget cut short is continued by the
  next pass, across a restart too. It searches nothing - finding a plan is the planner's.
  `agent/belief/deliberator.py`.
---

# Who runs it

Whoever its self graph states is a `belief:Deliberator`, directly or through a
[role](/domain/kernel/role.md) beneath this one — the [observer](/domain/sensing/observer.md), the
market's host and bidder. Role and part are one concept under one word, and belief is loaded for
such agents alone. It needs nothing of the world, and an agent holding no rules may still be declared one; but
an agent holding a rules graph that is no deliberator is refused at onboarding, since nothing it
runs would revise by those rules. Hanoi's mover is none — its world ships no rules — and the tower's
is one, for the rules that conclude Hanoi's facts from the grid's.

# What it does

It owns a queue. Whoever writes a graph — sensing an observation, prediction a stretch, speech a
peer's document, the executor a fictive step — says `changed(graph)`, and nothing happens then.
`deliberate()` is the pass: it runs [revise](/domain/belief/revision.md) over each queued graph beside
public knowledge and the state graphs the agent derived, spending at most a budget of rule executions
across all of them, and answers what it spent; and says by `revised` which graphs it revised, which
the executor hears to walk and sensing to write each [subject belief](/domain/sensing/subject-belief.md)
the rules judged. The [runtime](/domain/kernel/runtime.md) calls it where a pass needs the conclusions:
after what the transport delivered, before the planner.

A graph whose rules settled leaves the queue. One the budget cut short stays, its revision
graph's row saying `belief:settled false`; the next pass continues from what was concluded, and a
deliberator built on a lived-in store re-queues every such graph first, so a cut survives a
restart. A rule set that never settles spends its budget every pass and is said in the log rather
than looped on.

# The word, and the other one

In 0.1.0 "the deliberator" was the search that named the next move; that is the
[planner](/domain/planning/planner.md) now, and this is deliberation in the older sense — belief
revision, where what follows from what was written is concluded before anyone decides anything.
