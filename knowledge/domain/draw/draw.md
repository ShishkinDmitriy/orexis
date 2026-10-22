---
type: Process
title: Draw
description: >-
  Lots drawn by commit and reveal between two agents in a standing conflict - each says a hash of its number,
  then the number once the peer's hash is heard, and both conclude one winner from the two numbers. A domain
  of documents a world imports, so the fair coin can be read, tested and replaced; coordination reads only the
  outcome.
---

# The domain

`domains/draw/` is two actions, two extractions and an outcome, and a world of coordinators imports it
(two-agents-that-want-one-resource-ask-each-other-and-draw-lots-for-it). Each agent's desires drive it: *every
standing conflict's draw has my commitment* and *every draw the peer committed to has my reveal*, met-tests
over coordination's conflicts. A draw is the one a conflict names for its present round
([conflict](/domain/coordination/conflict.md)).

# Commit, then reveal

- **Committing**, `draw:Committing`, taken over each standing undecided conflict with a peer: its saying
  makes a `draw:Commitment` for that draw, carrying `draw:hash`, a hash of the draw's name and the agent's
  number, and its effect is what the agent believes once said, `draw:committedBy` the agent.
- **Revealing**, `draw:Revealing`, admitted only once the peer's commitment is believed, since a number shown
  first would let the peer choose its own after: a `draw:Reveal` carrying `draw:number`.

The number is a hash of the agent's secret and the draw's name: minted once at first boot, never said, so
nothing is kept per draw and a test that states the secret fixes every number. Each takes the peer and
nothing else: a conflict is the agent's own conclusion, which no world states, so an action taking it would
have no filling and no scope (#913).

# What is concluded

A commitment heard or said is extracted as said, with who committed to which draw and the round it is
drawn in (`coordination:drawnIn`); a reveal as said, number and all. The outcome, a `coordination:Outcome`
in the draw's rules, concludes `coordination:wonBy` once a peer's reveal hashes to the commitment the same
peer said and the agent's own commitment stands: the first hex digit of a hash of the draw and both numbers,
in the agents' order, odd for the lower-named agent. Both compute it from the same documents and conclude
alike; a reveal that does not hash to its commitment concludes nothing, and the draw restarts in the next
round.
