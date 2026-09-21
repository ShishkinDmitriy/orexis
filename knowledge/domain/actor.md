---
type: Service
title: Actor
description: >-
  The code a step is linked to — the module that carries a committed step out. Found
  through the action itself, which is an extension point: the kernel asks the choir by the
  action and never names a package. Every
  action is an extension point its taker contributes to — `@contributes(<the action>)` on a
  method `(act, desire, intention) -> bool` that turns a committed step into a nudge, a bid, a
  dose or a serve; False where it cannot act now, and the intention stands.
---

# What it is

An **actor** is whichever of an agent's modules takes a step. It is not a new kind of module:
the sensing module, the bidding module, the actuation module and the hosting module are the
actors, each for the [action](/domain/action.md) its package declared. What is new is that the
link from a row to its code is a **fact in the graph** rather than a dispatch table in Python.

# The link

```python
@contributes(OBSERVING)   # sensing, in both of its members
@contributes(ACQUIRING)   # the bidder
@contributes(DOSING)      # actuation
@contributes(OFFERING)    # the host
@contributes(SERVING)     # the host
@contributes(PRESENTING)  # the bidder
```

Each is a method on the module in the package that declared the action — the row and the code
that takes it are one directory, deletable together. WHO takes an action is read off that
contribution: the contributing class's capability, and the family it belongs to. A triple,
`orexis:takenBy`, used to restate it on the action node; once the method named its action the
triple said nothing the code did not, and it retired as a duplicate. [Executor](/domain/executor.md)
resolves a step by asking the choir by the action — `agent.ask(step.action, …)` — which reaches
exactly the family's providers, every member of it. That plural is deliberate: the gardener
holds two sensing modules and only one can nudge a probe; listening contributes a look that
declines, so the family answers and the look stands for the reading the device sends when it
will.

**An action nobody contributes is an action no plan can execute.** Hanoi's Move and the
courier's drives are that on purpose — worlds for the search, answered by hand in their tests.
An action some package contributes must be contributed by a provider each agent that holds the
family actually loads, and `tests/test_hooks.py`, `orexis-validate` and boot refuse otherwise,
rather than letting the ledger fill with commitments that stand for ever.

# The point

```python
@contributes(DOSING)
def dose(self, act, desire, intention: str) -> bool
```

An action IS an extension point: the signature and the cognitive row are declared once on
`orexis:Action` and every action inherits them, so a package fills the point for its own action
the way it fills any other. The one `take` hook every module implemented, with an if-chain on
the action inside, is gone with it. **A family is held to its actions** in three places:
`tests/test_hooks.py` over the whole tree — one action, one family, and at least one provider
contributing it — `orexis-validate` for each agent a world would build, and boot, where an
agent holding a family whose action none of its own providers contributes refuses to start.
That is what a package declaring an action for another family comes to: allowed by the
mechanism, refused by the gate until that family's provider contributes it, which is the
right place for the agreement to be visible.

`act` is the [act](/domain/act.md) the plan's head proposes — the action, the want and what it
is about, what its parameters are bound to, the quantity the search sized, and, for an obligation, whom it
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
amortised deliberation for every action and not only for the ones that happened to stand.

# What it is not

- **Not a decider.** An actor never asks the deliberator. The bidder's `submit` used to hold the
  last opinion about whether to pursue; it holds none now.
- **Not the [actuation](/domain/actuation.md).** That word is the supplier's actuation arm — the
  trusted end of a claim, one hop from the valve. An actor is a module in the agent's own
  process, and the actuation module is at once an actor (it takes `Actuate`) and the thing the
  executor page describes when it redeems a claim for someone else.
