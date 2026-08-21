---
type: Capability
title: Deliberation
description: The whether, extracted into a family — given the gap and the standing commitments, name the next move; the acting modules carry it out. Reflex is the old welded chain as the first member, deterministic and free; Consulting is the declared, unimplemented seat for a model, constrained before it exists — a move from the vocabulary's menu, never free text-to-action, with the bid number staying deterministic and the keeper's patience bounding how often it is consulted.
---

# What it is

The **whether**. Whether to look and whether to pursue used to be welded into the bidder — a
reading arrived and `value_bid`'s cede was the whole of deciding — which meant the one place
this project intends to seat a model
([llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md)) had no seam to drop into. It is
a family now: a deliberator is asked `propose(property, freshest value or None)` and answers
with a move — `Observe`, `Acquire` — or with None, **which is a decision, not an absence of
one**: the actors treat it exactly as they treat their own cooldowns.

`propose_for(goal)` is the same question asked properly. A property and a value can only ever
express a stake, and an agent also wants things that are not distances — "this claim redeemed"
is a state, wanted, with a deadline. A goal carries either shape and one urgency, so a duty is
ranked against a thirst rather than running down a second path that never meets the first.

**And it is where not-seeing is answered** (#240). `propose` used to open with
`if value is None: return OBSERVE` — a first line that read a missing number as ignorance. It
said the right thing for the wrong reason, because None meant two things: *never read*, and
*the caller has no number to hand you*. The keeper exploited the second to ask the first,
sweeping noticed gaps and passing None deliberately to mean "should I look?". A goal says which
epistemic failure it is — `unmeasured` or `stale` — so the question is now asked in the words it
means, both are answered by the same move, and the bare-value door steers only. One sentinel
answering two questions is a sentinel that eventually answers the wrong one.

# Deciding by simulating it

`propose_for` no longer answers only from the gap's sign. Where a lever's package has said what
that lever DOES, the deliberator builds the world taking it would make — `(beliefs − retracts) +
adds`, written nowhere — scores that world by the same `Region.urgency` every consumer reads, and
takes the move only if the result beats doing nothing.

The difference is not academic. A plant sitting ABOVE its region passes every test the reflex
applies: the pump raises moisture, the aim is above the reading, direction matches sign. Both are
true of a drowning plant, which is how a society floods one while every module behaves as written.
Simulation reaches the opposite answer without knowing anything about wetness — it builds the
world the dose would make, finds it no better, and declines. *Not better* is a decision.

Three things bound it, and each exists because building it found the failure:

- **A search that could not see every lever may not conclude that nothing helps.** Most means
  have no effect rule, and a plant in `world/simulation` BUYS its water — so a search there sees
  Observe alone, correctly finds that looking does not wet soil, and would have reported that
  nothing does. The plant would have stopped bidding. A plan that passed over any lever is
  marked partial, and a partial plan defers to the reflex.
- **The dose is asked of the actuator, never computed here.** `dose_for` is the sizing the actor
  would use; a planner that sized its own would simulate an act nobody was going to take. The
  first draft invented half a litre and manufactured a finding — every dose overshot, and the
  planner reported a rig too coarse to settle. The rig was fine.
- **A negative dose is not an act.** Sizing is `(aim − value) × conversion`, so a property above
  its aim asks for a negative pour, and the effect rule politely predicts the plant arriving back
  at its aim. The actor has always refused this; the refusal has to live on both sides.

- **A step is simulated from where it is TAKEN.** The bindings a rule is filled with were first
  computed from the goal and reused at every depth, so a second dose predicted what the first had
  and landed on the world the first one reached — discarded by cycle detection as somewhere
  already seen. The loop ran twice and the search was depth 1, for every means that moves a
  measured property.

**Every lever on a plant's menu states its effect now (#268), and until recently one did not.**
Only sensing and actuation shipped effect rules, so a plant that BUYS its water had a search
that saw Observe alone: it correctly found that looking does not wet soil, marked the plan
partial and deferred. `blind` was 1 for every plant and `better` was zero across three
societies. The market states what buying does, and the sizing is asked of whoever would take
the act — the bidder for Acquire, the actuator for Actuate. Asking the actuator about
everything is what made the first attempt worse than the blindness it replaced: a plant that
holds no valve was sized at nothing, the rule predicted the world the agent already stood in,
and the search reported that buying does not help. A partial plan defers; a confident one
overrides the reflex and stops the plant bidding.

**Depth 2 is honest now, and two separate things had to be true for it (#254).**

The first is that a rule is asked about a WORLD rather than about the store — which is what the
[imaginarium](/domain/imaginarium.md) is, and where the argument for it lives. Measured on the
loner's gardener before it existed: 0.08 beside 0.12 on one observation node after two doses,
with the value read back arbitrarily.

The second was found by fixing the first, and is why nobody had seen the two readings in a
running society. **A sensing action ends a plan, and the search enforced that with a rule of its
own** — it read `ag:confirmedBy ag:ByObservation`, which every effect here answers, a dose and a
bid included, because only a later reading says either arrived. So the guard matched every
lever, the frontier was empty at every depth, and the search ran at depth 1 whatever `MAX_DEPTH`
said.

**There is no guard now, and that is the fix rather than a shortcut.** What a look does is
already stated by its EFFECT: it predicts the value it found, so the world it reaches carries
its parent's signature and cycle detection discards it — by the same road a zero-size bid
arrives at "this does not help". Measured with the guard removed, on three worlds including a
first look with nothing sensed: Observe is pruned as a world already reached, every time. A
second statement of a fact the effect already settles is a fact that can disagree with it.

What that rests on is `_signature`, which is the goal's own value, and a look does not move it.
[#258](https://github.com/ShishkinDmitriy/agora/issues/258) asks whether a signature should
carry where a plan IS rather than only that number — and a signature noticing a fresher
`sosa:resultTime` would make "look, then look" a new world every time. Chaining past a look
becomes a real question again exactly there, and nowhere earlier.

**What limits depth now is the menu, not the machinery.** Fixing the baseline makes depth 2
honest; it does not make depth 3 useful, because what decides that is whether the levers compose
— [the-ladder-of-means](../decisions/the-ladder-of-means.md)' question rather than this one's.

**Legality is checked once, on the winner.** Validating every candidate against everything the
packages ship costs 1.73s against the goal shape's 0.083s — twenty times more, for an answer
about rules no effect could have broken — and a depth-2 pass would take twenty-two seconds
instead of under two. What must be true is that the agent never COMMITS to reaching a world the
society refuses, so the expensive question is asked of the world it actually intends.

# Watching it decide (#256)

Every one of those decisions used to die in-process as a single log line, and it could not be
recovered from outside: pyoxigraph holds an exclusive lock on the belief base, so nothing else
can open the store to re-run the search and see what it saw. That is the same fact `agora-ask`
exists for, arriving at the planner.

So a pass writes itself down. Per goal, into `graph/deliberation`, replaced at the start of the
next pass:

```sparql
SELECT ?goal ?verdict ?standsAt ?means ?via ?wouldReach ?why WHERE {
  GRAPH <http://example.org/agora/graph/deliberation> {
    ?d a ag:Deliberation ; ag:deliberatedOn ?goal ; ag:verdict ?verdict ;
       ag:standsAt ?standsAt ; ag:considered ?c .
    ?c ag:wouldTake ?means ; ag:through ?via ; ag:verdict ?why .
    OPTIONAL { ?c ag:wouldReach ?wouldReach } } }
```

Asked of the loner's gardener, wet at 0.42:

```
goal bounds.gardener.SoilMoisture   pass: not better   at 0.88
  considered Observe  via moisture_probe  would reach 0.88  — a world already reached
  considered Actuate  via pump            would reach 1.00  — no better than standing still
```

Which is the whole argument in four lines: the pump was weighed rather than passed over, and
watering would take this plant from 0.88 to **1.00** — worse. A reader gets the numbers, not the
verdict on trust.

**It is the record's one exception and not an exemption from the rule.** Possible worlds are
computed and dropped, except where a reader outside the process needs one — and then: its own
graph class, cleared at the start of every pass, PROV to what generated it, never public and
never in belief. All four hold. `ag:through` is the PROV: a trace that said only `Actuate` would
not answer *through which valve*, which stops being rhetorical the moment an agent holds two.

Three things it must not become:

- **A second pass replaces the first**, candidates and all. An orphaned candidate is a trace
  outliving the pass it described, which is the hazard the computed-not-stored rule exists to
  prevent — and the node is minted deterministically from the goal's IRI precisely so a restart
  can find and replace it. `hash()` would not do: Python salts it per interpreter, so every boot
  would orphan a trace instead of replacing one.
- **A restart inherits nothing.** The world moved while the agent was not running.
- **Nothing reads it back.** Cycle detection lives in the search, in a set that lasts as long as
  the pass. A trace that became memory would be a conclusion feeding a conclusion.

Not public, and the reason is not tidiness: which levers an agent weighed and rejected is a
disclosure nobody decided to make, and a rival reading it would learn what its neighbour can
nearly do. It is reachable the way an intention ledger is — the sovereign asks.

The aggregate rides the same tick: `agent_deliberation` carries a field per outcome, so a
dashboard shows how often an agent finds nothing worth doing. Six fields where a planner
returning a move or None gave two, and the pair worth watching is `no_candidate` against
`exhausted` — one says equip me, the other says my doses are too coarse. Counted from the trace
rather than tallied in the module, so the figure on a dashboard and the answer over the ask
channel cannot drift.

Writing it costs **0.7%** of a pass — 6.6ms against 0.96s, measured on the bench. A debugging aid
that slowed the thing it observes would be a poor trade.

# What a pass cost, and what it could not see

`agent_planning` carries the other half of the same trace: how long the pass took
(`ag:tookSeconds`, the one figure the trace could not already answer), how many worlds it built,
how deep it reached, and what it did with each lever — `met`, `better`, `worse`, `cycles`,
`unsimulated`, and `blind` for the goals where some lever had no stated effect at all. Read back
out of the trace rather than counted a second time, so the pass being measured is the pass that
happened; measuring by re-planning would double the cost it reports. Reading them costs **0.4ms**,
which is a tenth of one per cent of a pass.

**Three of the fields exist to make a recorded limit visible rather than to confirm health**, and
that is the argument for having them at all. `deepest` pinned at 1 is two limits at once — a
rule's CONSTRUCTs run against the store rather than the world, and the cycle signature is the
goal's own value, so a step that moves nothing else is indistinguishable from having gone
nowhere. `cycles` climbing beside it says which of the two is biting. `blind` above zero is a
package that never said what its lever does, which is why a partial plan defers to the reflex
instead of reporting that nothing helps.

**And the figure that surfaced something uncomfortable: a reporting tick IS a planning pass.**
`series()` calls `pursued()`, which re-plans every goal the agent holds, so essentially the whole
cost of reporting an agent's state — measured at ~0.4s for a fern with two goals — is deliberation
done over again to describe deliberation. Planning to decide happens on a reading; planning to
report happens on the tick; nothing shares the answer between them. That is not a defect in the
figures, it is what the figures found.

**All zero means nothing was deliberated**, not that planning is free: a want nobody has read is
answered by Observe before any search runs, so an agent at rest reports zeros honestly.

# The members, and which of them exist

Two of the three are built. The table is the whole answer to "which rungs can I rely on" —
`PROVIDES` in `packages/capability/deliberation/__init__.py` is the ground truth, and
`tests/test_knowledge.py` holds this table to it.

| member | what it is | built? |
|---|---|---|
| `deliberation:Reflex` | the welded chain, depth 1 | **yes** — `ReflexModule` |
| `deliberation:Planning` | bounded search, depth 2, granted by the dealer premise | **yes** — `PlanningModule` |
| `deliberation:Consulting` | one model call, emitting a move from the menu | **no** — declared and reserved |

The same asymmetry runs through the rest of the amortisation ladder, and it is worth seeing in
one place before reading the records that argue each rung:

| rung | where it lives | built? | record |
|---|---|---|---|
| look / act / buy | `deliberation:Reflex` | **yes** | [the-ladder-of-means](/decisions/the-ladder-of-means.md) |
| commit once, keep it | `intention:Keeping` | **yes** | [an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md) |
| plan two levels | `deliberation:Planning` | **yes** | [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) |
| re-pick your own settings | `review:Reckoning` | **yes** | [self-review-is-a-capability](/decisions/self-review-is-a-capability.md) |
| ask a model what next | `deliberation:Consulting` | **no** | [the-model-is-consulted-at-the-edge-of-knowledge](/decisions/the-model-is-consulted-at-the-edge-of-knowledge.md), [a-consulted-answer-is-a-premise](/decisions/a-consulted-answer-is-a-premise.md) |
| ask a model to re-pick | `review:Consulting` | **no** | [self-review-is-a-capability](/decisions/self-review-is-a-capability.md) |
| compile it into a habit | — | **no**, not even declared | [a-habit-is-a-compiled-deliberation](/decisions/a-habit-is-a-compiled-deliberation.md) |

**Declared is not implemented, and that is deliberate** — a term is declared when seating the
thing is the reason the family exists and the T-Box should say so. What each reserved member will
NOT be allowed to do is fixed before it exists, which is the point of declaring early.

- **`deliberation:Reflex`** — the old chain, generalised one honest step: cannot see → look;
  a gap on the side a lever moves → pursue; otherwise nothing. WHICH side is read off the
  T-Box, not known (#127): the domain states `market:direction` beside the denomination —
  water Raises moisture — so a heater against a cold snap is the same rule with no code
  change, and a missing direction means the reflex refuses rather than letting the old
  hardcoded sign sneak back as a default. Still deterministic, still free.
- **`deliberation:Planning`** — the reflex one level up (#205): bounded search over menu
  rows, depth 2 and no deeper, granted by the DEALER premise — acting for a source you offer,
  refillable from a source another offers: levers that compose. It subsumes the reflex and
  adds exactly one deduced goal past the region: the hosted lot must be serveable, every
  downstream buyer's silent Acquire precondition. Its plan — acquire upstream, then offer
  downstream — is data twice over: `plan_for` in code and `plan.rq` on the ask channel, one
  text, two readers. A planner always also derives Reflex (the premises nest); a pinned test
  holds `provider` to handing actors the planner.
- **`deliberation:Consulting`** — RESERVED. One model call over the beliefs, the T-Box, the gap
  and what already stands, emitting a move **from this vocabulary's menu, never free
  text-to-action**. Its constraints are fixed before it exists: the bid *number* stays
  deterministic ([deterministic-bid](/decisions/deterministic-bid.md) — the model picks whether
  and when, code computes how much); an intention it leads to validates against the same shapes
  or is not adopted; and the [keeper's patience](/domain/intention.md) bounds how often it is
  consulted at all, which is what makes it affordable.

# What stays out

- **The how.** A bid's quantity and price, a cadence, a dose — the actors', whoever said to act.
- **The keeping.** A deliberator may read what stands and never writes the ledger: deciding and
  remembering what was decided are different abilities, which is why keeping and deliberating
  are two capabilities on one granting premise (a stake and a lever) rather than one.
- **The host's trigger.** A host has no gap — its "whether to sell" is a stake in the *market*,
  the [strategic-supplier](/decisions/strategic-supplier.md) seam, and putting it here would
  hand a subject-shaped answer to a venue-shaped question. (An owed round is not a counter-
  example: physics defers it and the keeper remembers it — nothing here decides it. #206.)

# The menu — what I could do

The rows a deliberator ranges over. This package keeps only the frame and its consumers — it
shipped one big `menu.rq` here first, which made the menu's KINDS a registry in this directory
until the sovereign caught the overclaim.

**Chaining therefore needs no precondition language**, and that is the one thing about the menu
worth stating here rather than in [affordance](/domain/affordance.md), which owns why: the
search's "would this lever even exist afterwards" is the ordinary menu query, run against the
simulated world instead of this one. What a row carries, what an absent one means, and the two
modes are all over there.

# What the search does with an effect

Runs one per candidate, against the [imaginarium](/domain/imaginarium.md). What an
[effect](/domain/effect.md) IS, what it may claim, and its timing are that page's.

The consequence for this loop: a [means](/domain/means.md) carrying no rule cannot be simulated,
so the pass is marked PARTIAL and defers to the reflex. Concluding otherwise would be concluding
from part of the menu, and the row nobody could simulate may be the one that works — measured on
fern, which buys its water.

# What deliberation does with a duty (#218)

The reflex filters the menu to CHOSEN rows and never proposes an honoured one — the split
itself is [affordance](/domain/affordance.md)'s. What belongs here is why a duty is deliberated
about at all, since the obvious arrangement is that it is not.

Honouring used to be *never proposed*: the whether was settled elsewhere and by others — the
winner's Apply, the auction's allocation, the signature chain — and the fear was that a host
free to deliberate over claims is a host that can defect politely, one "None is a decision" at a
time. The fear was answered rather than ignored, and the answer is that **enforcement was never
the deliberation**. The dose still opens against a claim the pump's firmware verifies, clearing
still validated the trade, the ACL still bounds who may speak. What deliberation controls is
only whether the agent *tries* — so making the duty a want converts an invisible non-event into
a hot unpursued goal, which is evidence instead of silence. See
[an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md).

What it bought: this used to answer only *what could I do about MY gaps*, so an ability that
serves others — claims against my valves are redeemed — was a true fact about the agent that
lived nowhere queryable, and the sovereign asking what an agent does saw half its conduct. Now
one query answers both, and the dealer's own menu reads honestly: buy upstream, watch my stock,
and honour three pots' claims.

# What starts a pass

The keeper's tick. Where the work comes from, and why noticing stopped being the market's job, is
[gap](/domain/gap.md)'s.

# The proof the seam is load-bearing

`tests/test_deliberation.py`: silence the deliberator and a thirsty bidder with a fresh reading
in hand — everything the old welded bidder needed — submits nothing, because the whether
genuinely is not the bidder's any more. Before the extraction no test could have made that fail,
and it is the property a model member stands on: replace the answerer, touch no actor.
