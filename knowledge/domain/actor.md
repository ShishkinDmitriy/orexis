---
type: Service
title: Actor
term: http://example.org/orexis#takenBy
description: >-
  The code an affordance is linked to — the module that carries a committed step out. Found
  through one triple, `ag:takenBy`, which the package shipping a row states on the means the
  row offers, so the kernel dispatches by asking the T-Box and never names a package. Exposes
  `take(act, desire, intention)`, the choir hook that turns a committed act into a nudge, a bid,
  a dose or a serve; answers False where it cannot act now, and the intention stands.
---

# What it is

An **actor** is whichever of an agent's modules takes a step. It is not a new kind of module:
the sensing module, the bidding module, the actuation module and the hosting module are the
actors, each for the [action](/domain/action.md) its package declared. What is new is that the
link from a row to its code is a **fact in the graph** rather than a dispatch table in Python.

# The triple

```turtle
sensing:Observing   ag:takenBy sensing:SensingCapability .
market:Acquiring    ag:takenBy market:Bidding .
actuation:Dosing    ag:takenBy actuation:Actuation .
market:Offering     ag:takenBy market:Hosting .
market:Serving      ag:takenBy market:Hosting .
market:Presenting   ag:takenBy market:Bidding .
```

Each is stated on the [action](/domain/action.md) node itself, beside the precondition and the
effect it carries out — the row and the code that takes it are one directory, deletable
together. The object is a
capability term, so [executor](/domain/executor.md) resolves it exactly as any module reaches
another: `agent.providers(family)`, through the T-Box, and every member of the family is offered
the step. That plural is deliberate — the gardener holds two sensing modules and only one can
nudge a probe — and it is the same reason `providers` exists at all.

**A means with no `ag:takenBy` is a means no plan can execute.** None ships that way any
more — `ag:Offer` was the last, and `market:Offering` gave it a row, an effect and the host as
its taker. A package that ships a *row* for a means and states no taker has shipped an
intention nothing can carry out, and `tests/test_execution.py` refuses that at the gate rather than letting the ledger fill
with commitments that stand for ever.

# The hook

```python
def take(self, act, desire, intention: str) -> bool
```

`act` is the [act](/domain/act.md) the plan's head proposes — the action, the want and what it
is about, the [lever](/domain/lever.md), the quantity the search sized, and, for a duty, whom it
is owed to. `desire` is the want it
serves, `intention` the ledger row already written for it. What an actor does with them is its
own: sensing nudges every driver that can be asked; bidding reads the open round off the row's
own venue and bids into it; hosting announces a round for the call the plan served, or serves
the presented claim; actuation sizes a dose from the
current reading and commands it; hosting serves the presented claim. The *how* stays where it
always was — `value_bid`, `dose_for`, `redeem` — and none of them moved.

**False means "not now", never "no".** A bid with no round open, a bid the link cannot carry,
a dose with no fresh reading, a serve with no claim in hand: the actor declines, the intention stands, and the trigger that
changes the answer — an offer, a reading, a presentation — runs execution again, which finds
the standing row and takes it without re-deciding. That is what makes an intention an
amortised deliberation for every means and not only for the ones that happened to stand.

# What it is not

- **Not a decider.** An actor never asks the deliberator. The bidder's `submit` used to hold the
  last opinion about whether to pursue; it holds none now.
- **Not the [actuation](/domain/actuation.md).** That word is the supplier's actuation arm — the
  trusted end of a claim, one hop from the valve. An actor is a module in the agent's own
  process, and the actuation module is at once an actor (it takes `Actuate`) and the thing the
  executor page describes when it redeems a claim for someone else.
