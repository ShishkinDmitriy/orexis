---
type: Decision
title: Planning branches on action, forecasting on belief, and a look is a step in the second
status: accepted
timestamp: 2026-09-10T09:00:00Z
description: >-
  The sovereign's model of time, agreed 2026-09-09 and recorded before it is built. ONE tree of
  possible worlds and two kinds of edge: a CHOSEN one is a step the agent prefers among, a
  HAPPENING one is the world's and is only to be right about. The chosen are searched; the
  happening are folded into the node they belong to, because nothing chooses the weather. Every node carries a TIME, so two worlds holding the same facts at different
  instants are different worlds; a rule may read the clock its step lands at; exogenous
  uncertainty is a narrowing set of bands; and a LOOK, which changes no fact, is the step whose
  whole effect is in the second cone. Refused — searching the world's branches as if they were
  candidates, ranking them by expected value, a timeless node, and the special case that keeps
  looking alive today.
---

# The claim

**One tree of possible worlds, and two kinds of edge.** Every node of both cones is a
[possible world](/domain/imaginarium.md) at an instant, and that is the substance the two cones
share: a prediction is about possible worlds, and what an agent's actions do is move it among
them. What differs is not the nodes. It is WHO CHOOSES THE EDGE.

![one tree of possible worlds, its nodes labelled by the bands their readings are in, its chosen edges labelled with actions and its happening edges with what the world does](../diagrams/time-two-cones.svg)

The picture labels every node with the [bands](/domain/band.md) its readings are in, and every
edge with what takes it: an action on a chosen one, a thing the world does on a happening one.
Two paths reach a world where the want is met, and they are two worlds rather than one place
reached twice, which is item 1 below.

- **A CHOSEN edge is a step.** The agent takes it, so the world it leads to is one the agent may
  prefer among. This is the tree
  [the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md)
  already describes and #553 already built.
- **A HAPPENING edge is the world's.** Readings not yet taken: what the soil will show, whether
  it rains, whether the sun has set by the time a vent opens. Nobody prefers among these, so
  there is nothing on them to search.

**The modality belongs to the EDGE, not to the node.** A chosen edge is intention-shaped — it is
something to commit to; a happening one is belief-shaped — it is something to be right or wrong
about. That is why the two cannot be scored alike: ranking is meaningful over what an agent
chooses, and there is no preferring one weather to another. Folding the happening edges into the
node they leave rather than expanding them as candidates is therefore the semantics rather than
an optimisation.

Two things follow for whoever builds it. **One structure and not two** — the imaginarium already
holds this tree, and what item 3 below adds is a second kind of edge in it rather than a second
store. And the second kind is not a new idea here: `SURPRISE_EXOGENOUS` in the planner already
names a happening edge the search never drew, which is exactly what an exogenous surprise IS.

**Execution walks one kind of edge and settles the other.** Acting takes a chosen edge.
Observing settles which happening edge was taken while it was. The present is where both are
known, which is why [identification](/domain/identification.md) is doing two jobs at once:
deciding which path the agent is on, and which of the world's branches the real one landed in.

# What it explains that we had been working around

**A look changes no fact.** Its predicted world nets to nothing against its parent, so the
search discards it as somewhere already reached. Every attempt to make the planner value
looking has run into this, and the current answer is a special case: a step that MEETS a want is
not expanded from, so a look survives by not being a place to search onward from
(a-lever-an-agent-cannot-pull-is-not-a-lever).

Under this model the reason is plain and the workaround is unnecessary. A look takes a chosen
edge to a possible world holding the same facts — which is why its diff is empty — and FEWER
happening edges leaving it. It acts on the branching rather than on the world. The search cannot
see that because the search has no branching to see, and the fix is not a rule about looks. It
is the second kind of edge.

Sensing has said the sentence for a long time: *looking changes what you KNOW, not what is*.
What was missing was a place for it to have consequences.

# What follows, in the order it would be built

1. **A node carries a TIME**, and identity becomes world-and-when ([#587](https://github.com/ShishkinDmitriy/orexis/issues/587), landed). The world moves whether
   or not the agent does — soil dries at a declared rate nothing in planning reads, rain
   arrives, night falls — so two nodes holding the same facts at different instants are
   genuinely different worlds. Everything below waits on this, and it is the one change that
   touches cycle detection, which compared worlds with no notion of when.

   Built as `signature.where`: the node's diff and the path's own `orexis:landsAfter` summed,
   with every node of a pass counting from one root, so nothing reads a wall clock. Every
   shipped world plans exactly as before — the same forks and the same steps — because
   doubling back inside a budget needs an action that both declares a landing and returns to a
   pose, and no shipped world has one. What it costs where one does is measured on hanoi with a
   minute per move: three disks go from 50 forks to the whole 128-world budget, still seven
   moves, and no longer solved at that world's own 64. So the GRAIN two instants are told apart
   at is a seam, and it belongs to the drift below rather than beside it — see
   [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md).

   **What did not land with it is the drift** — the world moving between two instants — because
   an imagined reading has no number to move. Since an effect declares the band it reaches and
   no value, a drift cannot be arithmetic on the reading in hand; it is a statement that a
   reading in one band becomes a reading in another after long enough, which is the declaration
   item 3 exists for. It is [#592](https://github.com/ShishkinDmitriy/orexis/issues/592), and it waits on that.
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
4. **A look is a chosen edge that narrows the happening ones**
   ([#590](https://github.com/ShishkinDmitriy/orexis/issues/590)), valued by the narrowing it buys rather than by a
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
