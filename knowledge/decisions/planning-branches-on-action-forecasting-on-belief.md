---
type: Decision
title: Planning branches on action, forecasting on belief, and a look is a step in the second
status: accepted
timestamp: 2026-09-10T09:00:00Z
description: >-
  The sovereign's model of time, agreed 2026-09-09 and recorded before it is built. Two cones
  open from the present. The agent's branches on CHOICE and is searched; the world's branches on
  BELIEF — what I will come to observe — and is folded into each node, because nothing chooses
  the weather. Every node carries a TIME, so two worlds holding the same facts at different
  instants are different worlds; a rule may read the clock its step lands at; exogenous
  uncertainty is a narrowing set of bands; and a LOOK, which changes no fact, is the step whose
  whole effect is in the second cone. Refused — searching the world's branches as if they were
  candidates, ranking them by expected value, a timeless node, and the special case that keeps
  looking alive today.
---

# The claim

Two cones open from the present, and they are not the same kind of thing.

![the two cones](../diagrams/time-two-cones.svg)

- **The agent's cone branches on CHOICE.** Each edge is a step it may take, each node a world
  it would reach. This is the tree
  [the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md)
  already describes and #553 already built.
- **The world's cone branches on BELIEF.** Its edges are readings not yet taken: what the soil
  will show, whether it rains, whether the sun has set by the time a vent opens. What varies is
  not what the agent does but what it will come to believe.

**The distinction is a modality.** The first is intention-shaped: a branch is something to
commit to. The second is belief-shaped: a branch is something to be right or wrong about. That
is why they cannot be scored alike — ranking is meaningful over what an agent chooses, and there
is no preferring one weather to another. Folding the world's cone into each node rather than
expanding it as candidates is therefore the semantics rather than an optimisation.

**Execution collapses one and extends the other.** Acting adds a step to the intention cone.
Observing collapses a branch of the belief cone. The present is where both are settled, which
is why [identification](/domain/identification.md) is doing two jobs at once: deciding which
path the agent is on, and which branch of the world's cone happened.

# What it explains that we had been working around

**A look changes no fact.** Its predicted world nets to nothing against its parent, so the
search discards it as somewhere already reached. Every attempt to make the planner value
looking has run into this, and the current answer is a special case: a step that MEETS a want is
not expanded from, so a look survives by not being a place to search onward from
(a-lever-an-agent-cannot-pull-is-not-a-lever).

Under this model the reason is plain and the workaround is unnecessary. A look has no effect in
the intention cone at all. Its whole effect is in the belief cone, narrowing what the agent will
believe without changing what is. The search cannot see it because the search has no belief
dimension — and the fix is not a rule about looks, it is the second cone.

Sensing has said the sentence for a long time: *looking changes what you KNOW, not what is*.
What was missing was a place for it to have consequences.

# What follows, in the order it would be built

1. **A node carries a TIME**, and identity becomes world-and-when ([#587](https://github.com/ShishkinDmitriy/orexis/issues/587)). The world moves whether or
   not the agent does — soil dries at a declared rate nothing in planning reads, rain arrives,
   night falls — so two nodes holding the same facts at different instants are genuinely
   different worlds. Everything below waits on this, and it is the one change that touches
   cycle detection, which compares worlds today with no notion of when.
2. **A rule may read the clock its step lands at** ([#588](https://github.com/ShishkinDmitriy/orexis/issues/588)). The search already sums each step's
   `orexis:landsAfter`; the number exists and is never handed over. This is what makes a
   forecast readable at all, and it closes the seam the vent already has, where a plan that
   opens a window after dark is simulated against the afternoon
   ([effect](/domain/effect.md)).
3. **Exogenous uncertainty is a narrowing set of [bands](/domain/band.md)** ([#589](https://github.com/ShishkinDmitriy/orexis/issues/589)). Three days out a
   reading may be any band, tonight two, now exactly one. A forecast is an observation whose
   `sosa:phenomenonTime` is in the future, arriving `orexis:Received` from a service rather than
   an instrument, in a per-agent graph of its own — never the sensed graph, which upserts one
   reading per subject and property and means *now*.
4. **A look is a step in the second cone** ([#590](https://github.com/ShishkinDmitriy/orexis/issues/590)), valued by the narrowing it buys rather than by a
   fact it makes true. This is what makes *dose, look, dose* findable by a search rather than by
   re-planning after a surprise, and it retires the special case above.
5. **Long-lived and overlapping actions** ([#591](https://github.com/ShishkinDmitriy/orexis/issues/591)), the largest and last. If a step spans an
   interval rather than landing at a point, a plan stops being a sequence and becomes a partial
   order: dosing while the heater runs. `progression:then`, the ledger and the keeper's advance
   all assume a chain.

# What was refused

- **Searching the world's branches.** Expanding "it rains" and "it does not" as candidates puts
  the weather on the menu, and a menu is what an agent may DO. The branches are folded into the
  node they belong to, which is also what keeps the fork count from multiplying by the forecast.
- **Ranking them by expected value.** Probability would need a semantics for scoring a world by
  what it is worth times how likely it is, which changes how every world is ranked and what a
  plan even means. A narrowing set of bands says the same thing coarsely, in the domain's own
  words, and the keeper's verdict already catches a branch that did not happen. The cheaper
  mechanism is the one this project keeps choosing: the world verifies a plan, a search does
  not prove it.
- **A timeless node.** It is what we have, and it is why a plan can be simulated against a world
  six hours out of date and no gate says so. The cost of fixing it is real and named in item 1;
  the cost of not fixing it is a search that plans against a world that has stopped existing.
- **A rule about looks.** The special case works and is small, and it would go on working. It is
  refused because it explains nothing: it keeps a look alive without letting the search say why
  a look is worth taking, which is the question every *dose, look, dose* plan turns on.

# Seams left open

- **Whose forecast, and how trusted.** A reading is an instrument's word and the only arrival
  whose trustworthiness is a question; a forecast is a service's, further out and less
  answerable. It needs a horizon like any reading — past it, it is not evidence — and the
  freshness machinery is the natural place, applied to a fact about the future.
- **An agent talked out of acting by weather that never comes.** The verdict catches it and the
  next pass replans, so the cost is a delay rather than an error. Whether a want should refuse
  to wait past some point is a policy nobody has needed yet.
- **Two agents' belief cones.** Nothing here says what happens when what I will believe depends
  on what you will do. Beliefs about other agents stay first-order — what they DID, never what
  they believe — and this record does not move that line.
