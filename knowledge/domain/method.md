---
type: Domain Concept
title: Method
term: http://example.org/orexis#method
description: >-
  The steps taking an action comes to, in order, declared by the package that owns the action.
  The search chooses the action by its effect and its cost and never expands it; the keeper
  expands a step of it at adoption into the method's steps, the last inheriting the end, and
  walks them on feedback. Each step's action says what it waits for.
---

# What it is

A template of several steps, the way an [action](/domain/action.md) is a template of one: an
aggregation of actions, or of methods, with shared variables — combine templates and you get
a template. The axis is the one action and act already sit on. A method filled is a
**plan**; a plan's steps taken are acts. The search fills a method it composes on the spot
out of actions; the keeper fills a package's when it adopts the action that carries it; and
a plan that worked can be lifted back to its method, the same instance across steps becoming
the same variable, which is what would make it reusable (#469). An action with a method is a
method whose composed effect is stated by its package rather than computed from its steps.

`orexis:method`, an rdf:List on an action whose members are [actions](/domain/action.md) or
step nodes — `[ orexis:does <action> ; orexis:viaBy <select> ; orexis:aboutBy <select> ]`, a
member that fills its own lever and subject from the parent's by a template. HTN's shape: an
action the search chooses may be ABSTRACT — `market:Acquiring` is the decision to enter a
venue at a price — and what taking it comes to is a sequence the package declares: tender a
bid into the open round, then present the claim it wins. The search never sees the sequence.
It chooses Acquiring by the reading its rule predicts and by what it costs, exactly as before,
and hands the plan down whole ([intention](/domain/intention.md)).

The [keeper](/domain/intention.md) expands at adoption, recursively: a [step](/domain/step.md)
of an action with a method becomes one step per member, chained with `orexis:then`, and a
member with a method of its own expands in turn, so the ledger walks a flat chain. Each step is
`orexis:partOf` the filling it came from — the parent step stays in the ledger, off the chain,
so a reader can recover the tree. A bare member reuses the parent's lever and subject; a member
with templates binds them LATE, when the step becomes current, against the world as it then is:
the third move's disk is where the first two left it, and the first two have not happened at
adoption. The last member inherits the parent's `orexis:predicts` and predicted urgency, since
the end the search planned on is reached when the method is done. Then the plan is stepped as
any plan is — each step taken when the one before it is confirmed, the tail dropped on a
surprise.

# What a step waits for

A method's steps are not on any menu — no precondition, no effect — and each says what it
waits for as SELECT templates with the rules' own tokens (`$me`, `$via`, `$about`,
`$subject`, `$beliefs`, `$since` — the intention's adoption), bound when the step becomes
current:

- `orexis:readyWhen` holds the step before it is taken, as its `orexis:until`; a step whose
  condition already holds is taken at once, and one whose wait lapses is taken anyway, as a
  held claim redeems blind rather than never. Presenting waits for the bidder's watch to be
  live, or for a claim the host already redeemed.
- `orexis:doneWhen` holds the step after it is taken, as its `orexis:answeredWhen`, so the
  keeper advances on it; a wait that lapses is an unmet verdict, which drops the tail and
  asks deliberation again. Tendering is done when a claim on the venue cleared to me since the
  intention was adopted, and lapses at the round's close: losing a round is a step lapsing.
- `orexis:lapsesAt` says when either wait is over — a dateTime such as the round's close, or
  seconds from now such as the sensor's horizon — and the patience where it says nothing.

A step with none of these is taken when it becomes current and done when its action's
prediction is answered, which is every action that predicts a reading.

# What it is not

**Not a search.** The method's steps are never simulated; a method is what the package knows
about its own protocol, and the search's question is whether to enter it. What a method cannot
yet say is a member that IS a search — a sub-want planned when the step is reached, which is
what a travel across a grid is (planning inside another); that is the next piece.

**Not a branch.** A method is a sequence. Winning or losing is not two branches in the plan
but one step done or lapsed, and lapsing is the replanning road every plan takes.

**Not the reaction chain.** Before #523 the bidder's Python carried the protocol as
reactions — an offer, a bid, a claim held in a dict, a redeem — invisible to the ledger. The
claim is a fact in the bidder's own graph now (`market:Claim`), which is what lets a step
wait on it.

See [a-method-is-the-steps-an-action-comes-to](/decisions/a-method-is-the-steps-an-action-comes-to.md).
