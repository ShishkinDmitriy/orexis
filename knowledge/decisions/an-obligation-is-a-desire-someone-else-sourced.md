---
type: Decision
title: An obligation is a desire someone else sourced, and provenance says who
description: The sovereign's reframe of #218, and a better cut than the mode it replaces — the
  distinction belongs on the GOAL, not on the lever. A claim presented against my hardware
  raises a desire ("valve X open for three seconds") in a desire graph of its own, with PROV
  saying why it exists and whose it is; urgency is the common currency, so the hottest want
  wins whether it is my plant dying or a litre I owe. It is the second instance of a class the
  design reserved for several sources, the first real customer of the graph-desire widening,
  and BOID's override order is the shape of an agent's character.
---

# An obligation is a desire someone else sourced, and provenance says who

Proposed by the sovereign against the mode this record supersedes: *"it should be a goal
appeared — to open valve X for some time. And it could be a dedicated desire named graph,
with PROV about why this desire exists. It could be sourced by the agent itself or by a claim
from another agent — my obligations. Also we can add urgency for desire graphs, to choose the
hottest one."*

[#218](https://github.com/ShishkinDmitriy/agora/issues/218) put the distinction on the LEVER —
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
  region's centre scaled by the survival envelope on that side — so "my plant is dying" and "I
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

# Seams left open

- **How an obligation's urgency is computed.** A stake's urgency comes from the envelope; an
  obligation's has no envelope, and the honest candidate is its DEADLINE — the claim's own
  redeem window, rising as it closes, which makes lateness hot rather than making obligations
  permanently maximal. Getting this wrong in either direction is the whole risk: always-hottest
  is the mode by another name, never-hot is a defecting agent.
- **Where the override order lives.** A belief (the agent's character, revisable) or a world
  fact (the society's contract, ratified)? The mandate pattern says the sovereign should bound
  it and the agent pick inside — which would make "how social am I" a revisable belief inside a
  ratified band.
- **What a claim-sourced desire says exactly.** "Valve X open for three seconds" is an ACT, and
  desires here are states — so the honest form is the state the act brings about (this claim
  redeemed, that pot dosed), with the act remaining the affordance. Getting this wrong would
  put an action in the desire and lose the layer the whole architecture rests on.
- **What becomes of the honoured row.** Disclosure survives the reframe: a lever that serves
  others is still worth showing the sovereign and a model. What does not survive is the mode as
  a FILTER on deliberation, since an obligation is meant to reach it.
