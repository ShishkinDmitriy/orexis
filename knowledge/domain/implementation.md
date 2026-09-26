---
type: Domain Concept
title: Implementation
term: http://example.org/orexis/execution#Implementation
description: >-
  How an action is carried out — what actually goes out when a step filling it is taken, sized
  from the present. An `execution:Implementation` holding operations grouped by `sh:order`. The
  search never reads it; the world is held to the effect whichever operations carried it out.
---

# What it is

An [action](/domain/action.md) says when it may be taken (its [precondition](/domain/precondition.md)),
what taking it makes true (its [effect](/domain/effect.md)), and, in its `execution:implementation`,
how it is taken. The last is a set of [operations](/domain/operation.md), and the search is blind
to it on purpose: a plan picks the act and never its size or its wording, which are decided when
the step is taken, from the situation as it then is.

Operations are grouped by `sh:order` exactly as an effect's rules are. Those of one order are all
made from the same present; a later order's are made from the present after what the earlier ones
said has been believed and revised, so a saying at order 1 can read what the same step said at
order 0. An absent order is 0, and every shipped action is one order.

An action with no implementation is taken by saying its name in the log, which is what a step of
an action nobody carries out comes to.

# Where it is read

The executor reads it to tell whether a step is fictive; the runtime reads it to take a step,
order by order, sending what each command answers through the transport and believing, revising
and telling what each saying makes (`agent/execution/implementation.py`).
