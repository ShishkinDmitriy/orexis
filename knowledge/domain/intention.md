---
type: Domain Concept
title: Intention
term: http://example.org/orexis/progression#Intention
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
  claim opens an expectation — baseline copied into the row, promised direction from the domain,
  deadline from the patience — and the verdict lands beside the outcome, so
  satisfied-and-unmet is recordable, the false-knowledge signature. An open expectation is maximum
  urgency, so the cadence tightens until the world answers; an affordance unmet suspectAfter
  times running is flagged, never auto-retracted.
---

# What it is

**An intention may be held until a condition holds** (#512). The keeper adopts an act with a
select over the agent's beliefs and a deadline; it re-asks the select whenever a belief lands
and keeps the deadline on its scheduler. The first time the select binds, the act is handed to
whoever takes it; if the deadline passes first, the act is taken as lapsed or dropped, as the
adopter said. The condition sits on the [step](/domain/step.md) the intention stands at — an
intention is the commitment, which want and why; the step is the planned instance, and a
planned thing is what waits; the [act](/domain/act.md) is the record of its taking — as data on
the ledger (`progression:until`, or its twin
`progression:untilNot`, released when the condition stops holding — hold while the round is open),
and it is always a SHAPE — a condition that is naturally a query is a shape carrying a
`sh:sparql` constraint, the form SHACL already has — which the keeper compiles to the select
it runs (conformance for `until`, violation for `untilNot`) while the ledger keeps the shape,
so a sovereign asking sees what an act waits for as it was written (#514). The market's held [claim](/domain/claim.md) is this path with the
live watch as its condition, and a plan's next step is this path with the previous step's
prediction as its condition. This is the middle layer's whole job in one call — adopt, wait,
take on feedback — and it is why nothing above it needs a timer of its own.

**And an expectation on a reading is the predictor's comparison, told the intended branch**
(#639). When an act is taken, the keeper tells whoever predicts — sensing, through
`orexis:predicted` — the band the step declared for the reading (#510, #579), from when a
reading may answer (`progression:expectedFrom`), when the step lands (`progression:landsAt`)
and the deadline; it holds no shape and knows no reading. Sensing compares each reading of
the key with the band once at arrival and answers (`Keeper.answered`): in the band, met —
early is the dose landing; outside it at or after the landing, unmet; before the landing,
nothing. The deadline passing first is the verdict unmet, the keeper's alone. A PLAIN fact
the step predicts is still held as a shape, its COMPLETION condition
(`progression:answeredWhen`, beside its readiness condition `progression:until`), and a
number a caller states is held to the band it falls in, the number kept for the residual.
A plan handed down whole holds each step's readiness on the previous step's answer.

**And it is the plan, whole** (#510). Deliberation hands every step down; the intention has
`progression:step` to each, stands at the head, and moves along `progression:then` as the world confirms
each step's prediction — the met verdict on one step is the only license the next has, and no
search runs while a plan is in progress. An unmet verdict stops the plan where it is: the
intention resolves, the tail is abandoned, and deliberation is told to plan again. A met verdict
on a step whose want is ALREADY MET finishes the plan there (#521): the world did more than the
step promised, the intention resolves satisfied with the tail finished rather than taken, and
what was walked is the steps to that one — advancing would hand the next step to an actor that
sizes it to nothing and leave the intention standing at a step nobody will take. "Only the
head is committed" was the rule before feedback could carry a plan; it is superseded. A step
of an action that declares a [method](/domain/method.md) is expanded at adoption into the
method's steps (#523), and each of those may wait — before it is taken, or after — on what its
action declares.

Two paths adopt one. A plan's head, chosen by the search, is the ordinary path; an event
adopts the other — the market's Presenting, an [action](/domain/action.md) stating neither a
precondition nor an effect, which a claim arriving adopts and a watch going live triggers —
with no search above it, and both stand in the same ledger and wait on the same kind of
expectation.


A **commitment**: one want pursued by one action, adopted at a moment and standing
until the world answers. BDI's third letter, and the one this project ran longest without —
`bidding.pending` was an intention to observe and a bid awaiting its claim was an intention to
acquire, both living as Python attributes that died with the process and answered to nothing.
They are rows in a graph now, each with `adoptedAt`, a resolution (`satisfied` | `dropped`) and
a `becauseOf` in both directions, because a commitment abandoned without a reason is
indistinguishable from one forgotten.

**The deliberator ticks (#208)**: on the keeper's patience it marks every want for the
[reviser](/domain/reviser.md), whose worker hands each to [executor](/domain/executor.md), which plans, commits the head and hands it to its actor —
for every means, not only the look. Deliberation stopped being something only the
market can start: a marketless property's watching reaches this ledger too, Observe adopted
when stale and satisfied by the reading, whoever caused the look. A healthy society's gap
entries are ZERO — they mark need, not routine.

**An intention is an amortised deliberation.** Intentions exist to *save* deciding: an agent
that re-decides on every reading is a reflex machine wearing a planner's name. Here that is a
cost model rather than philosophy — deliberation is about to include an LLM call
([the decision record](/decisions/an-intention-is-an-amortised-deliberation.md)), and the
standing intention is what makes one affordable: committed means not re-consulted.

# The actions an intention names

| means | the act | adopted | resolved |
|---|---|---|---|
| `sensing:Observing` | get a reading where the gap is unmeasured or stale | the bidder starts waiting on its sensor | the look comes back (satisfied) or the auction closes first (dropped, with why) |
| `market:Acquiring` | bid for what would reduce a gap | a round is open and the search picks it — by the offer, or by the tick while it stands | the claim arrives (satisfied), or the round closes without one (dropped, whether told or by the clock) |
| `market:Presenting` | spend a held claim against the world | the claim arrives — holding IS the intention | the claim is presented on the redeem channel (watch live, or the bounded wait) |
| `market:Offering` | open a round on a hosted venue | the search plans it for a [call](/domain/call.md) — at once, or after the refill it also plans | the round opens (satisfied by construction) |
| `actuation:Dosing` | move it myself — action and resource both mine (#190) | the search finds this rung reaches a better world than buying | the watch on the end is judged — met or unmet — the row standing from the command until then (#353); the dose itself co-signed and confirmed like any other |

`Observe` is first for a structural reason: at birth there is a desired state and an empty
sensed graph, so the first intention is always to look — see
[desire](/domain/desire.md) §the gap.

`Acquire` is committed to the **gap, not the round**: adopted with the first bid, absorbed for
every further bid while it stands, satisfied by the claim — **and satisfied is only the
MEANS**. The claim opens an *expectation* on the end (below).

`Apply` is **real since #132**, and earlier than the futures market it was reserved for: the
reason to hold a claim turned out to be *observability* before it was temporal strategy — never
spend a dose you cannot watch land. Adopted when the [claim](/domain/claim.md) arrives,
standing while the holder waits for its watch to be provably live (the #135 ack at the fast
cadence, or a bounded wait that redeems blind rather than never), satisfied when the claim is
presented. A held claim answers maximum urgency exactly as an open expectation does — the hold
is the expectation one step earlier — and the expectation itself opens at presentation, when the dose
becomes imminent, so the baseline is not aged by the hold. Futures now merely extends the
holding period this gave a mechanism to.

# The expectation — the end, judged apart from the means

Before #131, an Acquire resolved when the claim arrived and nothing ever checked whether the
gap moved: an agent whose water never reached the pot bought, recorded satisfied, and bought
again forever — transaction confirmed, outcome never audited. Now resolving the means opens a
**expectation**: the step gains the *baseline* (value and instant, copied into the ledger because the
sensed graph keeps only the current witness — the ledger is what remembers) and a *deadline*: the
act's landing time plus how long a reading takes to arrive, both passed by the actor, or the
patience where the act cannot say.

What the world is held to is **the step's own prediction** (`progression:predicts`, #510) — the facts
the search said taking it makes true and false, the same facts its signature is made of — and
the actor sizes nothing: it says only how close, a [tolerance](/domain/tolerance.md) on the
predicted movement. The keeper generates the answering shape from the prediction and holds the
step on it as `progression:answeredWhen`: a predicted reading is put to sensing, which answers with
an observation later than the baseline within the tolerance of the predicted value; a plain
fact is the kernel's, present for an addition and gone for a retraction. Conformance before the
deadline — **met**. Deadline passed without it — **unmet**. An overshoot is as much a surprise
as a shortfall, and both are the conversion's to answer for at review. The first noisy world
closed an expectation on +0.001 two seconds before its dose arrived and let the same gap be bought
twice (#167 — the bidder still declines a new acquisition while its own dose is unanswered,
bounded by the expectation's deadline); a band around the prediction is what makes grain not an
answer. The verdict is a separate fact beside the outcome, and **satisfied-and-unmet is the
false-knowledge signature**: the graph claims a movement the world keeps refusing.

Two consequences ride on the expectation:

- **it is maximum urgency.** Evaporation is fractions per day; a dose lands in seconds — and
  urgency-by-state relaxes attention exactly when the dose needs watching, because the value
  improves. So the keeper answers sensing's ordinary `urgency` ask with 1.0 while an expectation is
  open (bounded by its deadline), and the cadence round-trips by itself: tight on adoption,
  released on verdict. Opening the expectation also asks for one look (`sense_now`), so the freshest
  before is on record.
- **enough unmet makes an affordance SUSPECT.** `suspectAfter` consecutive unmet ends for one
  (action, want) pair — consecutive, so one success resets: mostly-paying is noisy, not
  false — raises a warning and a health-series flag (`affordances_suspect`). Flagged, never
  auto-retracted: what to do about a belief that is not paying is a decision, and deleting
  knowledge would be reaching down a level
  ([control-the-derivative](/decisions/control-the-derivative-not-the-value.md)).

# The patience

The one piece of policy the keeper owns. Within `progression:patienceS` — each agent's own belief,
bounded by the family's constitutional floor and ceiling like a cadence — a second impulse to
adopt the same commitment is **absorbed**: `adopt` returns None and the caller treats it as its
own cooldown. Past it, a new adoption **supersedes**: the old one is resolved as dropped with
the outwaiting recorded, because honouring a dead commitment forever is as wrong as honouring it
not at all.

# Granted by a stake AND an action

Each capability is granted by whatever fact makes it meaningful. A commitment is to reduce a
named gap by a named means, so the premise is both halves: `orexis:actsFor` a subject that states
needs (else nothing to commit *about* — the supplier, all actions and no stake, keeps no ledger)
and at least one of a market position, an actuator, or a schedulable sensor (else nothing to
commit *to* — wanting without means is a wish). `world/sensing`'s agent fails the first half and
records.

# What it is not

- **Not a decider.** Nothing here chooses what to commit to; [executor](/domain/executor.md)
  calls `adopt` with the head of a plan, and the *whether* lives in
  [deliberation](/domain/deliberator.md). A row written here names, `progression:by`, the [act](/domain/act.md) the
  plan's head is — the action it fills, one triple per parameter it is filled with, the quantity the taker sized,
  the window — so the [actor](/domain/actor.md) handed it later takes the same act. Keeping and deciding share a granting premise and stay two capabilities
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
  [deliberator](/domain/deliberator.md) asking what already stands before deciding.
  Reflex does not ask yet; the member that will is the one that pays per decision.
