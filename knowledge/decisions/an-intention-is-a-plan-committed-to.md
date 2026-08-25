---
type: Decision
title: An intention is a plan committed to, and an affordance names the code that takes it
description: >-
  Execution was split by trigger: the keeper's tick carried out Observe alone, the bidder
  re-decided when a round knocked, the actuator decided on its own reading, and each adopted
  its own intention. Now there is ONE road — plan, commit the head as an intention, hand it to
  the actor the means names — and the link from a row to the code that takes it is a triple,
  `ag:takenBy`, stated by the package that ships the row. What changed is who carries a
  decision out, never how one is reached.
status: accepted
timestamp: 2026-08-24T18:00:00Z
---

# What was true before

The search was one road and execution was three. `Keeper.deliberate_on_gaps` asked the
deliberator about every want and then carried out only `Observe` — the docstring said so, and
said why: an Acquire needs a round nobody may convene from the buy side. The bidder waited for a
round to knock, looked, and asked the deliberator *again* inside `submit`, so a pass whose
answer the tick had already found was run a second time against the same world. The actuator did
the same on its own reading. Each of the three adopted its own intention with its own reason and
resolved it on its own event, and the ledger was written from three places by three authors.

That was BDI with the third letter half-done. A plan produced a *means*, a string; what got
committed was a means and a property; and which module carried it out was decided by whoever
happened to be holding the trigger. The planner's rows already said *through which lever* — the
`via` column, the half of a step the record on
[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) insists on
— and it was dropped on the way to the ledger.

# What is decided

**An intention is the head of a plan, committed to.** `Deliberator.decide(desire)` returns the
[plan](/domain/deliberation.md) itself — rows, not a means — and what the keeper writes is the
first row whole: `ag:by` the means, `ag:through` the lever, `ag:pursues` the desire. Only the
head, and that is not a shortcut: the plan is re-derived every pass because the world moves, so
a committed tail would be a promise about a future nobody has seen. The tail is in the trace for
a reader; the head is in the ledger for the agent.

**Carrying it out is one process, [execution](/domain/execution.md), and it is the kernel's**:
plan, commit, take. `agent/execution.py` is the whole of it, and every trigger goes through it —
the keeper's tick for every want, a fresh reading for the actuator, a round knocking for the
bidder, a presentation for the host. Nothing decides on the way: a trigger says *now*, the
search says *what*, the ledger says *committed*, and the actor says *done*.

**Every affordance is linked to the code that takes it, by a triple.** An [action](/domain/action.md)
states `ag:takenBy` a capability, in the ontology of the package that ships the row —
`ag:Observe ag:takenBy sensing:SensingCapability`, `ag:Acquire ag:takenBy market:Bidding`,
`ag:Actuate ag:takenBy actuation:Actuation`, `ag:Apply ag:takenBy market:Hosting`. Execution
asks the T-Box for the family and `agent.providers(family)` for whoever is loaded, and calls
`take(row, desire, intention)` on each — the choir's newest hook, beside `notices` and `urgency`.
The kernel names no package, and which code takes a step is a fact a sovereign can query —
where `planner._dose` still spells the two sizing families by hand, because sizing a bid and
sizing a dose are different questions with different names. A package that ships a row and no
`ag:takenBy` has shipped an intention nothing can carry out, which
`tests/test_execution.py` refuses. See [actor](/domain/actor.md).

**The bidder answers a round from what stands.** A standing `Acquire` is a commitment spanning
rounds — that was always its documented meaning — so an offer arriving while one stands is
executed, not re-decided: look, then bid. Only an offer arriving with nothing standing asks the
search, once, and adopts. The three passes a round used to cost (`on_offer`, `submit`, the
metrics tick) are one, and `submit` no longer holds an opinion about whether to pursue.

# What did not change, and why

- **The search.** Not a line. The imaginarium, the effects, the scoring and the trace are as
  [deliberation](/domain/deliberation.md) describes them. This record is about who carries an
  answer out.
- **"Look, then bid" is still two intentions, not one plan.** The freshness want and the region
  want are different desires; an unmet epistemic want answers first by sensing's `want_about` rule;
  a look nets to nothing in the signature so it never extends a frontier. All three facts stand,
  and the sequence you see in the logs — Observe committed, satisfied by the reading, Acquire
  committed, satisfied by the claim — is two desires pursued in the right order rather than one
  plan with a step chosen blind.
- **The host's trigger.** A host has no gap, and whether to *sell* is the
  [strategic-supplier](/decisions/strategic-supplier.md) seam. (`ag:Offer` was adopted on
  deferral by hosting and carried no `ag:takenBy` when this was written; since
  [a-round-is-a-fact-and-offering-is-an-action](/decisions/a-round-is-a-fact-and-offering-is-an-action.md)
  it is an action serving a [call](/domain/call.md), and the seam is unchanged: plannable is
  not wanted.)
- **The patience, and who answers it.** `adopt` still absorbs a commitment that STANDS within
  patience, and that is the whole rule for a means whose commitment outlives the act — an
  Acquire stands from bid to claim, and the round after the claim is a new impulse the open
  expectation (#167) governs. The actuator's guard for the act that resolved at the command
  (the 584-dose morning) was kept at first as an `absorbs` hook asked before committing;
  generalising it to every means was refused by `test_expectation`, and the hook itself was
  retired when the Actuate intention was made to stand until its verdict — see
  [an-intention-stands-until-the-world-answers](/decisions/an-intention-stands-until-the-world-answers.md).

# Seams left open

- ~~**The round is still an event, not a fact.**~~ Closed by
  [a-round-is-a-fact-and-offering-is-an-action](/decisions/a-round-is-a-fact-and-offering-is-an-action.md):
  a round is a belief on both sides, the Acquire row exists only while one is open, and
  nothing stands to buy between rounds.
- **The tail is trace, not ledger.** `ag:plannedThen` would be one triple and a reader outside
  could see a two-step plan on the intention that heads it. Not written until something reads it:
  a projection nobody consumes is a claim that can rot.
- **`take` returns a boolean and execution logs on False.** What an agent should DO about a row
  its actor declined — a bid with no round, a dose with no fresh reading — is today "stand and
  wait for the trigger", which is right for both shipped cases and is not a rule.
