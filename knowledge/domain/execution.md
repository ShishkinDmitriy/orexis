---
type: Process
title: Execution
description: >-
  What happens to a decision — plan, commit the head as an intention, hand it to its actor.
  ONE road for every trigger, in `agent/execution.py`: the keeper's tick, a fresh reading, a
  round knocking and a claim presented all arrive here and none of them decides. A step already
  standing is taken without a second search, which is where the amortisation an intention
  promises actually happens; a step nothing takes is logged, and the intention stands.
---

# Phases

1. **Plan.** `deliberator.decide(desire)` — the search, unchanged, returning its
   [plan](/domain/deliberation.md) as rows. No steps means nothing to execute, and that None is
   the deliberator's decision, not this process's.
2. **Commit.** First the actors the means names are asked `absorbs(row, desire)` — whether
   this is an impulse they already answered within patience, which only an act that resolves
   the instant it is commanded can say. Then the head row goes to the keeper:
   `adopt(means, property, desire=…, via=lever)`. The [intention](/domain/intention.md)
   written carries the lever the plan chose. If one already stands within patience, `adopt`
   returns None and the process ends here — the same impulse, absorbed, and no row written
   either way.
3. **Take.** The means' `ag:takenBy` family is asked of the T-Box, `agent.providers(family)` of
   the runtime, and each [actor](/domain/actor.md) is handed the row. At least one True is the
   step taken; all False is logged and the intention stands for the next trigger.

Two doors, and both are the same three phases: `pursue(agent, desire)` for a want in hand, and
`pursue_about(agent, property)` for an actor holding a fresh reading — the property door picks
the want by the rule [deliberation](/domain/deliberation.md) states, an unmet epistemic want
first, and goes through the desire door.

# What starts it

| trigger | who | what it used to do instead |
|---|---|---|
| the patience tick | keeper | plan every want, carry out Observe alone |
| a reading recorded | actuation | ask the deliberator, adopt, dose — its own copy of all three |
| an offer, reading in hand | bidding | ask the deliberator inside `submit`, adopt, bid |
| a claim presented, or stock arriving with one held | hosting | ask the deliberator, serve if it said Apply |

**A standing step is executed, not re-decided.** The bidder's case is the one that mattered: an
`Acquire` adopted on the tick stands until a round arrives, and the offer then goes look → bid
with no search in between. A round used to cost three passes over one world; it costs one.

# What it is not

- **Not a planner.** It holds no imaginarium, scores nothing, and never sees a candidate the
  search rejected.
- **Not a second keeper.** It calls `adopt` and never writes the ledger; the one-writer scan in
  `tests/test_intention.py` still holds.
- **Not the tail.** Only the head is committed, because the plan is re-derived every pass and the
  world moves between them — the argument is
  [an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md)'s.
