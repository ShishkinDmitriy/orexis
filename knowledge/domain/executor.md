---
type: Service
title: Executor
description: >-
  What happens to a decision — plan, commit the head as an intention, hand it to its actor.
  ONE path for every trigger, cut at the line where deciding stops and doing starts —
  `pursuit.py` in the deliberation layer plans and commits, `execution.py` in progression
  takes, on the reactive loop: the deliberator's tick, a fresh reading, a round knocking and a
  claim presented all arrive here and none of them decides. A step already
  standing is taken without a second search, which is where the amortisation an intention
  promises actually happens; a step nothing takes is logged, and the intention stands.
---

# What it runs

**Execution** — plan, commit the head, hand it to its actor. One path, whatever the trigger,
in two files since the kernel split along its layers
([a-layer-is-a-package-and-need-loads-it](/decisions/a-layer-is-a-package-and-need-loads-it.md)):
`packages/orexis-agent-deliberation/pursuit.py` holds `pursue` and `pursue_for` — the search
and the commit — and `packages/orexis-agent-progression/execution.py` holds `carry_out`,
`take_standing` and `taken_by`, the path from a committed act to its actor. The cut is at the
one line where deciding stops and doing starts, which is also where the search's thread
stops and the reactive loop begins: only a plan's HEAD crosses, committed and taken as one
item on the executing thread.

# Phases

1. **Plan.** `deliberator.decide(desire)` — the search, unchanged, returning its
   [plan](/domain/deliberator.md) as rows. No steps means nothing to execute, and that None is
   the deliberator's decision, not this process's.
2. **Commit.** The whole plan goes to the keeper — every [step](/domain/step.md), the head stood at — and the head is taken; each further step is taken when the world confirms the one before it (#510):
   `adopt(action, want, because, via=action)`.
   The [intention](/domain/intention.md) written carries the action the plan chose. If one
   already stands within patience, `adopt` returns None and the process ends here — the same
   impulse, absorbed, and no row written. That is the whole of the patience, because every
   means stands until the world answers
   ([an-intention-stands-until-the-world-answers](/decisions/an-intention-stands-until-the-world-answers.md)).
3. **Take.** The choir is asked by the action — every action is a point — and the module contributing it takes it;
   the runtime, and each [actor](/domain/actor.md) is handed the act. At least one True is the
   step taken; all False is logged and the intention stands for the next trigger.

Two doors, and both are the same three phases: `pursue(agent, desire)` for a want in hand, and
`pursue_for(agent, want)` for an actor holding a fresh reading — which want a reading is about
is [sensing](/domain/sensing.md)'s to say (`want_about`: an unmet epistemic want first, then the
region want), so the actor hands the kernel a NODE and goes through the desire door. The kernel keys
nothing by property ([the-region-want-is-sensings-want](/decisions/the-region-want-is-sensings-want.md)).

# What it reads and writes

![executor — what it reads and writes](../diagrams/service-executor.svg)

**It writes no graph of its own**, which is the shape of a service that only orchestrates: the
keeper writes the ledger, the actor does the thing, and the link from a row to its code is one
triple nobody here names.

# What starts it

| trigger | who | what it used to do instead |
|---|---|---|
| the patience tick | deliberator, marking; the reviser's worker pursues | plan every want, carry out Observe alone |
| a reading recorded | actuation | ask the deliberator, adopt, dose — its own copy of all three |
| an offer, reading in hand | bidding | ask the deliberator inside `submit`, adopt, bid |
| a claim presented, or stock arriving with one held | hosting | ask the deliberator, serve if it said Apply |

**A standing step is executed, not re-decided.** The bidder's case is the one that mattered: a
round is decided once — by the offer or by the tick while it is open, whichever comes first —
and the other finds the `Acquire` standing and searches nothing. A round used to cost three
passes over one world; it costs one. Between rounds nothing stands to buy, because the row does
not exist ([a-round-is-a-fact-and-offering-is-an-action](/decisions/a-round-is-a-fact-and-offering-is-an-action.md)).

# What it is not

- **Not a planner.** It holds no imaginarium, scores nothing, and never sees a candidate the
  search rejected.
- **Not a second keeper.** It calls `adopt` and never writes the ledger; the one-writer scan in
  `tests/test_intention.py` still holds.
- **Not a re-decider.** The tail is committed with the head, and the keeper steps along it on
  the world's feedback; this pass does not search while that plan is in progress — the argument
  is [progression-steps-through-a-plan-on-confirmed-feedback](/decisions/progression-steps-through-a-plan-on-confirmed-feedback.md)'s.

# In Agent 2.0, the executor owns the intentions

`agent/execution/executor.py` is the keeper and the executor of the 1.0 layers in one
service, because the intentions store is one thing and one owner writes it. It commits a plan
under the patience as the keeper did, and it carries the plan out: whatever plan is among
the intentions is scheduled, whoever wrote it there, since the planner's crossing writes them
without asking. Two threads and no more. The timekeeper asks which standing intention has a
head step whose `execution:notBefore` has passed and hands it to a queue, then sleeps until
the earliest step still waiting or the poll cadence; it runs nothing. The executing thread
drains that queue and waits on nothing else, so a slow step delays the steps behind it and
never the clock. Each thread's loop is one public door, `tick` and `drain`, and a test drives
a plan through its steps at instants of its choosing by calling the two, which is what keeps a
threaded run and a tested run the same run. Taking a step writes an `execution:Act` — when the taker was handed it and when it
returned, the record beside the step's `notBefore` and `landsAt`, which are the plan's
requirement and prediction — and then the world moves the intention.
A step carries what it predicts, the diff of the world it reaches against the one it leaves
as the canonical facts a digest is made of; from its `landsAt` on, every pass of the
timekeeper asks the present whether every predicted addition holds and every retraction is
gone, over the agent's readings, and moves `execution:by` along the chain when it does. The
last step resolves the intention `done`; the landing passed by the patience with no answer
resolves it `failed`, and so does a taker that raises. The executor never replans: it says
what happened, and the planner's next pass stands in the present that surprised it. A pure
simulation has no instrument to answer, so an action may be FICTIVE, its row saying so and
the extraction carrying it onto its steps: the executor writes such a step's prediction into
the readings itself, and the present answers because nothing else could have. An executor
built fictive takes every step so. The taker is one callable handed the step's rows, and today it
says the step's name in the log; how an action names the code that takes it is not decided.

