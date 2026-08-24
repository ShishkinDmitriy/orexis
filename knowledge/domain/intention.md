---
type: Domain Concept
title: Intention
term: http://example.org/orexis#Intention
description: >-
  BDI's third letter, and the KERNEL's — every agent keeps a ledger, because a mind is not
  plug-in-able and the intention STORE was already built for every agent while the thing that
  writes it was a grant. A commitment to reduce a named gap by a named means, persisting until
  satisfied, dropped or outwaited rather than being re-decided on every sensing. Kept in a
  private ledger with an adoption, a resolution and a reason; the patience that absorbs repeat
  impulses is each agent's own belief, and it is the STANDING rule alone — every means stands
  until the world answers, an Actuate from the command to its verdict (#353), where a dose
  satisfied at the command once stood for nothing and a gardener pulsed its pump 584 times in
  a night. Since #131 the MEANS and the END are judged apart: an acquire's
  claim opens a watch — baseline copied into the row, promised direction from the domain,
  deadline from the patience — and the verdict lands beside the outcome, so
  satisfied-and-unmet is recordable, the false-knowledge signature. An open watch is maximum
  urgency, so the cadence tightens until the world answers; an affordance unmet suspectAfter
  times running is flagged, never auto-retracted.
---

# What it is

A **commitment**: reduce the gap in one property, by one means, adopted at a moment and standing
until the world answers. BDI's third letter, and the one this project ran longest without —
`bidding.pending` was an intention to observe and a bid awaiting its claim was an intention to
acquire, both living as Python attributes that died with the process and answered to nothing.
They are rows in a graph now, each with `adoptedAt`, a resolution (`satisfied` | `dropped`) and
a `becauseOf` in both directions, because a commitment abandoned without a reason is
indistinguishable from one forgotten.

**The keeper also ticks (#208)**: on its own patience clock it hands every want to
[execution](/domain/execution.md), which plans, commits the head and hands it to its actor —
for every means, not only the look. Deliberation stopped being something only the
market can start: a marketless property's watching reaches this ledger too, Observe adopted
when stale and satisfied by the reading, whoever caused the look. A healthy society's gap
entries are ZERO — they mark need, not routine.

**An intention is an amortised deliberation.** Intentions exist to *save* deciding: an agent
that re-decides on every reading is a reflex machine wearing a planner's name. Here that is a
cost model rather than philosophy — deliberation is about to include an LLM call
([the decision record](/decisions/an-intention-is-an-amortised-deliberation.md)), and the
standing intention is what makes one affordable: committed means not re-consulted.

# The three means

| means | the act | adopted | resolved |
|---|---|---|---|
| `sensing:Observe` | get a reading where the gap is unmeasured or stale | the bidder starts waiting on its sensor | the look comes back (satisfied) or the auction closes first (dropped, with why) |
| `ag:Acquire` | bid for what would reduce a gap | a round is open and the search picks it — by the offer, or by the tick while it stands | the claim arrives (satisfied), or the round closes without one (dropped, whether told or by the clock) |
| `ag:Apply` | spend a held claim against the world | the claim arrives — holding IS the intention | the claim is presented on the redeem channel (watch live, or the bounded wait) |
| `market:Offer` | open a round on a hosted venue | the search plans it for a [call](/domain/call.md) — at once, or after the refill it also plans | the round opens (satisfied by construction) |
| `actuation:Actuate` | move it myself — lever and resource both mine (#190) | the search finds this rung reaches a better world than buying | the watch on the end is judged — met or unmet — the row standing from the command until then (#353); the dose itself co-signed and confirmed like any other |

`Observe` is first for a structural reason: at birth there is a desired state and an empty
sensed graph, so the first intention is always to look — see
[desire](/domain/desire.md) §the gap.

`Acquire` is committed to the **gap, not the round**: adopted with the first bid, absorbed for
every further bid while it stands, satisfied by the claim — **and satisfied is only the
MEANS**. The claim opens a *watch* on the end (below).

`Apply` is **real since #132**, and earlier than the futures market it was reserved for: the
reason to hold a claim turned out to be *observability* before it was temporal strategy — never
spend a dose you cannot watch land. Adopted when the [claim](/domain/claim.md) arrives,
standing while the holder waits for its watch to be provably live (the #135 ack at the fast
cadence, or a bounded wait that redeems blind rather than never), satisfied when the claim is
presented. A held claim answers maximum urgency exactly as an open expectation does — the hold
is the watch one step earlier — and the expectation itself opens at presentation, when the dose
becomes imminent, so the baseline is not aged by the hold. Futures now merely extends the
holding period this gave a mechanism to.

# The expectation — the end, judged apart from the means

Before #131, an Acquire resolved when the claim arrived and nothing ever checked whether the
gap moved: an agent whose water never reached the pot bought, recorded satisfied, and bought
again forever — transaction confirmed, outcome never audited. Now resolving the means opens a
**watch**: the row gains the *baseline* (value and instant, copied into the ledger because the
sensed graph keeps only the current witness — the ledger is what remembers), the *promised
direction* (the domain's own `market:direction`, #127, copied so the row stays judgeable), and a
*deadline* (the patience, until something derives a better horizon from the dose and the
physics — a recorded seam).

Every reading is a chance to judge: past the baseline in the promised direction — **met**, early
is fine, that is the dose landing — and past it by at least `metFraction` of the act's own
stated size where the act could size itself (`expectsDelta`, #165): a lying instrument can
breathe past a baseline, and the first noisy world closed a watch on +0.001 two seconds before
its dose arrived, which then let the same gap be bought twice (#167 — the bidder now declines a
new acquisition while its own dose is unanswered, bounded by the watch's deadline). Deadline
passed without it — **unmet**. Movement the wrong way *before* the deadline proves nothing,
since a dose may land late. The verdict is a separate fact beside the outcome, and
**satisfied-and-unmet is the false-knowledge signature**: the graph claims a movement the world
keeps refusing.

Two consequences ride on the watch:

- **it is maximum urgency.** Evaporation is fractions per day; a dose lands in seconds — and
  urgency-by-state relaxes attention exactly when the dose needs watching, because the value
  improves. So the keeper answers sensing's ordinary `urgency` ask with 1.0 while a watch is
  open (bounded by its deadline), and the cadence round-trips by itself: tight on adoption,
  released on verdict. Opening the watch also asks for one look (`sense_now`), so the freshest
  before is on record.
- **enough unmet makes an affordance SUSPECT.** `suspectAfter` consecutive unmet ends for one
  (means, property) pair — consecutive, so one success resets: mostly-paying is noisy, not
  false — raises a warning and a health-series flag (`affordances_suspect`). Flagged, never
  auto-retracted: what to do about a belief that is not paying is a decision, and deleting
  knowledge would be reaching down a level
  ([control-the-derivative](/decisions/control-the-derivative-not-the-value.md)).

# The patience

The one piece of policy the keeper owns. Within `ag:patienceS` — each agent's own belief,
bounded by the family's constitutional floor and ceiling like a cadence — a second impulse to
adopt the same commitment is **absorbed**: `adopt` returns None and the caller treats it as its
own cooldown. Past it, a new adoption **supersedes**: the old one is resolved as dropped with
the outwaiting recorded, because honouring a dead commitment forever is as wrong as honouring it
not at all.

# Granted by a stake AND a lever

Each capability is granted by whatever fact makes it meaningful. A commitment is to reduce a
named gap by a named means, so the premise is both halves: `ag:actsFor` a subject that states
needs (else nothing to commit *about* — the supplier, all levers and no stake, keeps no ledger)
and at least one of a market position, an actuator, or a schedulable sensor (else nothing to
commit *to* — wanting without means is a wish). `world/sensing`'s agent fails the first half and
records.

# What it is not

- **Not a decider.** Nothing here chooses what to commit to; [execution](/domain/execution.md)
  calls `adopt` with the head of a plan, and the *whether* lives in
  [deliberation](/domain/deliberation.md). A row written here carries `ag:through` the lever
  that plan chose, so the [actor](/domain/actor.md) handed it knows which valve or venue. Keeping and deciding share a granting premise and stay two capabilities
  because their replaceable parts differ.
- **Not public.** The ledger is a graph of the agent's own, like its beliefs and its revisions:
  an intention disclosed is strategy leaked, and the **bid is the public face** of an intention
  to acquire. The market sees what you do, never what you are trying to bring about.
- **Not a gate on the actors.** The ledger records what is done and never blocks it; what a
  standing intention absorbs is re-adoption, not the acts. Its consumers are the health series
  (`intentions_standing`, `oldest_intention_s` — a commitment growing old is an agent whose
  world stopped answering, invisible in every other series precisely because nothing is
  happening; a dose in flight counts here since #353, as it should — it IS a commitment), the operator reading why an agent did what it did — since #125 without SPARQL:
  every transition is projected with its `becauseOf` prose into the agent's own bucket and
  drawn as a Grafana annotation over the health series, see
  [agent-metrics](/domain/agent-metrics.md) — and, the one it was built for, a
  [deliberator](/domain/deliberation.md) asking what already stands before deciding.
  Reflex does not ask yet; the member that will is the one that pays per decision.
