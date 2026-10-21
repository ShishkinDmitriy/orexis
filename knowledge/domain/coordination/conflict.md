---
type: Domain Concept
title: Conflict
term: http://example.org/orexis/coordination#Conflict
description: >-
  Two agents that want one resource, as each concludes it from its own documents - an answer said or heard
  that was not empty, under a constraint both hold - standing while the peer is in range. Its draw decides
  who goes first; until then both yield, once decided the loser does, and a silent peer is yielded to.
---

# Concluded by each

No agent is told there is a conflict. Each reads the answers it said and the answers it heard: one that
carries a [holding](/domain/coordination/holding.md), under a constraint both hold, is a conflict with that
peer, read by the same rule by both (`agent/coordination/conclude.py`). Two answers between the same pair under
one constraint are one conflict, named for the pair and the constraint, so both name it alike and draw once.
It is written into a belief of the agent's own, derived, which the [draw](/domain/draw/draw.md)'s actions
read.

**It stands while the peer is believed in range**, whatever the answers say after: two plans that no longer
meet are what yielding made of them, and ended there the laying that keeps them apart would stop. A peer
believed nowhere ends it, and a later answer that is not empty begins it again in a later round.

# Rounds, and who won

A standing conflict's draw is the one of its present round, named for the conflict and the round, so nothing
of another round or another pair can be said into it. Who won it is concluded by an **outcome**
(`coordination:Outcome`): an `sh:construct` a world's rules ship, concluding `coordination:wonBy` of a draw,
which coordination asks each pass over everything the agent believes and writes beside the conflict. It is
asked and not triggered: a peer's word arrives as a statement no reader of the mind is handed, and what is
extracted of it is the agent's own, which triggers no [transition](/domain/belief/transition.md).

Undecided past the agent's patience, the draw restarts in the next round; a peer heard drawing in a later
round brings the agent to it. Past the rounds the agent states of itself, the peer is **silent**,
`coordination:silent`, and the agent yields to it as a loser does: it takes the whole of the avoiding, and
what it sees of the peer is what keeps it off the peer.

# What each lays

Yielding is laying the peer's holdings as [forecasts](/domain/kernel/forecast.md) of the peer's thing, the
agent's own and received, so the grounds take them in where each begins (`agent/coordination/lay.py`):

- **undecided**, both lay all of the other's, so each plans as if yielding and safety never waits on the draw;
- **lost, or silent**, the loser lays all of the winner's, for as long as the conflict stands;
- **won**, the winner lays the loser's next holding alone: the change of a step the loser may have taken
  before the draw reached it, which nothing the draw decides cancels - [commitment](/domain/execution/commitment.md)
  is hard on the step in flight.

At each instant a holding changes, what is laid is every value any holding then gives - between a step's
earliest landing and its latest the thing may stand at either. One already begun is laid into the present
beside what sensing says, since the van may still be between cells; and a holding the agent's own constraints
refuse beside what it believes now - a peer's van on a hedge only this agent's radar has seen - is not laid,
since every world after it would be impossible.
