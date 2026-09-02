---
type: Domain Concept
title: Triggered action
term: http://example.org/orexis#TriggeredAction
description: >-
  Progression's kind of action, not deliberation's: an intention adopted by an event and taken
  on a trigger, never chosen by a plan, so it states neither a precondition nor an effect and
  is on nobody's menu. Still an action, so the ledger names it and an expectation can wait on
  it. The vocabulary says which kind an action is rather than leaving it to absence.
---

# What it is

`orexis:TriggeredAction`, a subclass of [action](/domain/action.md) — and the layer it belongs
to is the middle one. The search never sees it. A message arrives through the transport and
becomes an event on the reactive loop; the keeper adopts an [intention](/domain/intention.md)
for it; a second event is the trigger; and the capability takes the act on the loop thread.
That is progression's whole road — adopt, wait, take on feedback — with no deliberation above
it, and this class is that road's word for the action at the end of it.

The market's Presenting is the one shipped: a bidder holds a won [claim](/domain/claim.md)
until the watch is live, then presents it on the redeem channel. No plan chooses that — the
claim arriving IS the adoption, the watch going live is the trigger — and it exists as a node
so the hold can be a commitment (`orexis:by`) and can carry an urgency.

# How to use it

**Declare the kind, and state nothing else.** A triggered action carries no `orexis:available`
and no `sh:construct`. The gate (`deliberable`, in `onboarding/validate.py`) refuses one carrying either:
a triggered action with a precondition is a choosable one mislabelled.

**A choosable action states both.** The other kind — the menu's — states a precondition and an
effect, and the gate refuses one lacking either, because the search is the only road to a
lever since the reflex was absorbed, and a lever the search cannot simulate is one nothing can
take. That gate is what retired the runtime's flags for a lever passed over: a pass no longer
reports itself partial, the trace carries no `blind`, and the planner skips nothing.

**Never on a menu.** The [afforder](/domain/afforder.md) runs preconditions, and a triggered
action has none, so it yields no row, is outside [relevance](/domain/relevance.md)'s closure, and
the search never sees it. What reaches it is an event, through the capability that takes it.
