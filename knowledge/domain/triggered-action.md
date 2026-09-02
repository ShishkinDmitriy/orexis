---
type: Domain Concept
title: Triggered action
term: http://example.org/orexis#TriggeredAction
description: >-
  An action no plan chooses: adopted by an event and taken on a trigger, so it states neither
  a precondition nor an effect and is on nobody's menu. Still an action, so an intention can
  commit to it and a ledger row can name it. The other kind of action, and the vocabulary says
  which is which rather than leaving it to absence.
---

# What it is

`orexis:TriggeredAction`, a subclass of [action](/domain/action.md). The market's Presenting is
the one shipped: a bidder holds a won [claim](/domain/claim.md) until the watch is live, then
presents it on the redeem channel. No plan chooses that — the claim arriving IS the adoption,
the watch going live is the trigger — and it exists as a node so the hold can be a
[commitment](/domain/intention.md) (`orexis:by`) and can carry an urgency.

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
