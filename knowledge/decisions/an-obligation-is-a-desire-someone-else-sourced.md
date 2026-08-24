---
type: Decision
title: An obligation is a desire someone else sourced, and provenance says who
description: >-
  The sovereign's reframe of #218, and a better cut than the mode it replaces — the
  distinction belongs on the GOAL, not on the lever. A claim presented against my hardware
  raises a desire ("valve X open for three seconds") in a desire graph of its own, with PROV
  saying why it exists and whose it is; urgency is the common currency, so the hottest want
  wins whether it is my plant dying or a litre I owe. It is the second instance of a class the
  design reserved for several sources, the first real customer of the graph-desire widening,
  and BOID's override order is the shape of an agent's character.
status: accepted
timestamp: 2026-08-19T10:13:28Z
---

# An obligation is a desire someone else sourced, and provenance says who

Proposed by the sovereign against the mode this record supersedes: *"it should be a goal
appeared — to open valve X for some time. And it could be a dedicated desire named graph,
with PROV about why this desire exists. It could be sourced by the agent itself or by a claim
from another agent — my obligations. Also we can add urgency for desire graphs, to choose the
hottest one."*

[#218](https://github.com/ShishkinDmitriy/orexis/issues/218) put the distinction on the LEVER —
a menu row was `Chosen` or `Honoured`, and the deliberator filtered duties out. This puts it on
the GOAL, which is deeper and simpler: there is one kind of row (what is possible) and one kind
of motivation (a want, with a source), and an agent's whole conduct is desires it pursues
through affordances. Nothing needs a second decision path.

## It is the seat the design reserved

`ag:ConstraintGraph` has been a CLASS since desire was built, and its comment says why: *"a
class rather than one graph, because desire may have more than one source and a reader must not
have to know how many."* One source has existed all along — the region deduced from the ranges
a subject states. This is the second, and it needs no new reader: `store.query` merges every
instance into the default graph, and `agent.genesis` already resolves a rule's write target from
the class.

Three more pieces are already in place:

- **Urgency is the common currency.** It is unit-free by construction — distance from the
  region's centre scaled by the survival envelope on that side (the anchor has since moved to
  the aim: [a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md)) —
  so "my plant is dying" and "I
  owe fern a litre" become comparable, which is exactly what the sovereign asked for and what
  no code could do today: the stake path and the claim path run in different currencies and
  never meet.
- **PROV answers WHY.** A self-sourced desire is derived from the subject's stated ranges; an
  obligation is derived from a signed claim. The guardrail this project cares about most is
  therefore preserved: a desire still answers to something public, and an agent may RECEIVE a
  desire but never AUTHOR one. The self-satisfaction loophole stays shut in both directions.
- **It is the graph-desire widening's first real customer.**
  [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) recorded
  desires-as-graphs with the honest note that nothing shipped needed it. An obligation is a
  goal that is not "a property inside a region" but "this claim is redeemed" — a graph diff,
  wanted, with a deadline.

## Why a deliberating host is not a defecting host

The objection that produced the mode was: a host that decides whether to honour claims can
defect politely, one "None is a decision" at a time. It dissolves here, because **enforcement
was never the deliberation**. The dose opens against a claim the PUMP'S FIRMWARE verifies
(trust-boundary, thin-trusted-infra); the ledger makes bought-at and sold-at subtractable; the
ACL bounds who may speak at all. What deliberation controls is only whether the agent *tries*.
So making the duty a desire does not weaken a guarantee — it converts an invisible non-event
into a hot unpursued goal, which is the evidence-producing posture this project takes toward
theft, false knowledge and every other misbehaviour it cannot prevent outright.

The literature name for the shape is BOID — Beliefs, Obligations, Intentions, Desires — where
obligations are first-class beside desires and the agent's CHARACTER is the override order: a
social agent lets obligations dominate, a selfish one does not. That maps onto
[control-the-derivative](/decisions/control-the-derivative-not-the-value.md) without strain:
the sovereign ratifies the ORDER (or the weighting), never the individual decision, exactly as
it ratifies a mandate rather than a belief.

## What shipped first, and why in that order

Implemented as DATA before it drives acts, deliberately: a claim issued raises a
`ag:Obligation` in a graph of the agent's own — counterparty, claim, presented-flag, two
timestamps — stepped to demanded on presentation and discharged when the dose goes out, kept
after payment because a debt paid and a debt forgotten must not look alike. Redemption itself
still runs where it always ran, so nothing regressed while the motivation layer grew under
it.

Two things fell out immediately. The debt is now DURABLE — a host kept its issued claims in a
module dict that died with the process, and a restarted host forgot every one — and the
counterparty is CHECKED: `owe` refuses an agent the world does not declare, which is the
guardrail that keeps "a claim raises a desire" from meaning "anyone may raise a desire in
me". Whom I may owe stays topology, disclosed by the honoured row and never stored.

The mode survives the reframe as DISCLOSURE rather than exemption: an honoured row says which
of my levers others may demand and by whom. The reflex still passes over those rows, and the
reason narrowed usefully — not "a duty is nobody's to decide" but "this member steers a
property toward an aim, and a duty is a graph-shaped goal it cannot express". That filter
lifts when a member can pursue a diff rather than a distance.

## What driving acts changed (step 9)

The motivation layer had been data for a while; this is where it started moving hardware, and
three things surfaced that the design had not.

- **The deadline did not exist.** The seam below proposed the claim's redeem window as an
  obligation's source of urgency, and the window was not a fact anybody held: a `Claim` carried
  who, how much, what it cost and an anti-replay id, and nothing about how long it was good for.
  So the choice was to invent a proxy or to add the missing data, and the sovereign chose the
  data. `market:redeemWindowS` is stated by the SOURCE — a venue is keyed by its source, so one
  owner offering two goods can hold each for a different time — and carried onto the derived
  venue, where the host reads it and stamps `exp` on every claim of the round.

  The first cut required it in the derivation, and a test caught what that cost: with the window
  in the rule's WHERE, a source stating `market:matchesBy` and nothing else derived NO VENUE —
  so consent had quietly come to cost two triples, against a claim this project makes on purpose
  and guards elsewhere. The venue now arises on consent alone and the shape refuses it for
  lacking a window, which is the difference between a world that is refused and a world that is
  silently smaller than its author thought.
- **A deadline makes expiry expressible, and expiry is a third state.** A claim presented after
  its window is refused: the venue stops holding the paper and the debt stays on the books,
  undischarged, with a deadline in the past. Paid, never-demanded, and ran-out are now three
  distinguishable things, where the first draft had two.
- **The honoured row found a second job.** It was disclosure — what others may demand of me —
  and it is now also how a duty finds its LEVER: an obligation names its counterparty, and the
  row honoured for exactly that agent is the means. The mode survived by being useful twice,
  which is the better argument for keeping a distinction than the one it was introduced with.

What did NOT change is the guarantee. Redemption still opens against a claim the pump's firmware
verifies, clearing still validated the trade, the ACL still bounds who may speak. What moved is
whether the agent *tries* — so the defection worry is answered by evidence: a duty nothing can
serve stays owed, stays hot, and says so in the log and the ledger, where before it was a claim
silently dropped from a dict.

## Owing is its own capability (#233)

A debt was kept inside `desire:Deducing`, whose premise is a STAKE — `ag:actsFor` a subject that
states what it needs. `world/simulation`'s city has no stake: it acts for a mains that states a
capacity and no ranges. So it deduced no region, composed no desire module, and recorded not one
of the claims it had been issuing and redeeming all day. Under the step-9 framing that is the
worst possible place for the gap to be: an unserved duty is supposed to be evidence, and the one
agent whose failure to deliver would leave none was the one best placed to fail.

Two abilities had been sharing one premise that covered only one of them. **Deducing a region is
meaningful because you have a stake; owing is meaningful because others can DEMAND your levers.**
So `desire:Owing` is its own capability, granted by its own fact — a venue this agent opened and
an actuator drawing from its source, which is the honoured row's premise read from the side of
the agent that will be asked. A plant has no such lever and keeps no ledger; the city keeps one
and still wants nothing for itself; the supplier has both and is unchanged.

**Goals stopped being one module's.** No single module can see them all now, so `Module.wants()`
joins `annotate`, `series` and `notices` as a choir hook, and `agent.goals()` merges and ranks
what the modules contribute. `pursued()` — each goal with the move proposed for it — belongs to
the DELIBERATOR, because counting what nothing can be done about needs the wants and the moves
together, and because the kernel may not name a capability's family.

**What it cost to learn:** the first grant rested on `market:hosts`, and matched nothing. Rules
run ONCE, in package-directory order, so `desire/` runs before `market/` and a premise resting on
another package's CONCLUSIONS sees an empty graph — silently, granting nothing. The same three
facts were sayable in authored and entailed terms (`market:matchesBy`, `market:offeredBy`,
`actuation:drawsFrom`), which is what every other cross-package premise here already does.

# Seams left open

- **How an obligation's urgency is computed.** ANSWERED, by the sovereign, and by adding the
  fact rather than working around its absence: it is the fraction of the claim's redeem window
  that has run — cool at issue, maximal at the deadline, clamped after. Both timestamps are kept
  on the obligation because the urgency is the room BETWEEN them; an agent holding only the
  expiry would have to assume when the window opened. The two failures this shape was chosen
  against are recorded because they remain the risk if anyone re-tunes it: a duty pinned at 1.0
  is the honoured mode returning under another name, since it outranks a plant that is dying,
  and a duty with no heat is an agent that defects while its ledger looks tidy.
- **Where the override order lives.** A belief (the agent's character, revisable) or a world
  fact (the society's contract, ratified)? The mandate pattern says the sovereign should bound
  it and the agent pick inside — which would make "how social am I" a revisable belief inside a
  ratified band.
- ~~**What a claim-sourced desire says exactly.**~~ CLOSED by
  [#255](https://github.com/ShishkinDmitriy/orexis/issues/255), the way the note said it had to
  be: the state is *this claim discharged* — a pattern over the record the planner's met-test
  asks of whatever world it judges — and the act stayed an affordance (`ag:Apply`, whose
  effect rule now states what serving makes true, sized from the record's own `ag:amountL`).
- **What becomes of the honoured row.** ANSWERED: disclosure survived, the filter did not, and
  the row gained a job nobody had planned for it — it is how a duty finds the lever that serves
  its counterparty. The reflex still passes over honoured rows when it is steering a PROPERTY,
  which is not a filter but an inability: a duty is not a distance, and that member cannot
  express one.
