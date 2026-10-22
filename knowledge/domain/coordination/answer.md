---
type: Domain Concept
title: Answer
term: http://example.org/orexis/coordination#Answer
description: >-
  What a peer says back to a question under a constraint it holds too - its own holdings that meet the asked
  ones, the two read together by the constraint's own select, or none. A question over a constraint the peer
  does not hold gets no answer at all, which the asker takes as silence.
---

# Only under a shared constraint

The answerer looks for the named constraint among those its self holds (`planning:holds`); where it holds
none of that name it says nothing, as a distributed constraint problem passes values only along the
constraints that link two agents (`agent/coordination/answer.py`).

# Only what meets

An answer carries the answerer's own [holdings](/domain/coordination/holding.md) under the constraint that
violate it beside some asked one: the two things, with the kinds the answerer believes them of and the values
the two holdings give, put to the constraint's own select, and a row is a meeting. A key alone could not tell
the courier's two constraints apart, which share their key; the select can. Nothing outside the asked
constraint's key, values and periods crosses.

# Said whatever it carries

An empty answer is said too: it is the whole cost of no [conflict](/domain/coordination/conflict.md), one
document each way. It is said in a graph named for the answerer, the asker and the constraint,
`coordination:AnswerGraph`, so it is replaced each time the question is said again.
