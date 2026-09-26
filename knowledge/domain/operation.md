---
type: Domain Concept
title: Operation
term: http://example.org/orexis/execution#Operation
description: >-
  One thing taking a step does — a command to a device, a document to a peer, or writing the
  step's own effect for a world nothing reports on. The parts of an implementation; the kinds are
  execution's.
---

# The three kinds

- **`execution:Command`** carries an `sh:select` answering `?actuator` and `?payload`, the JSON a
  device is sent: how much to pour, how long to heat.
- **`execution:Saying`** carries an `sh:construct` whose result is documents, each to the agents
  it names, believed by the agent as said and told through the transport
  ([speech](/domain/speech.md)).
- **`execution:Fictive`** carries no text: the step's predicted diff is written into the readings,
  because the world is the store and nothing else could answer — a hanoi move, a courier's drive.

Each is made from the present when the step is taken, with the step's parameters as `$tokens`,
`$me` and `$now`, and the [implementation](/domain/implementation.md) it belongs to says in which
order.

# Not an act

An operation is declared once, on the action, as part of how it is carried out; taking one step
may perform several. What taking it leaves behind is one [act](/domain/act.md), which is a word
for history and not for the doing.
