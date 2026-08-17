---
type: Decision
title: Means form a ladder, and the market is about the resource, not the lever
description: Look, act with what is yours, buy what is not, ask what you do not know — each
  rung costlier and more social than the last. Direct actuation is legitimate exactly where
  both the lever AND the source are the agent's own; owning the pump does not exempt anyone
  from the auction when the water is common. Consulting is the rung above the empty menu.
---

# Means form a ladder, and the market is about the resource, not the lever

Asked by the sovereign as three cases, which turned out to be rungs. An agent with a gap in a
property it desires has, in rising order of cost and sociality:

1. **Observe** — cannot see, so look. Always on the menu, always the first intention at birth.
2. **Actuate** — the lever is mine and the resource is mine: move it directly. No negotiation,
   because nothing anyone else owns is touched.
3. **Acquire** — the lever or the resource is another's: bid. The request IS a bid, contention
   is discovered by the host, and scarcity resolves by auction — with the quiet case already
   graceful, since an uncontested round dissolves to cost under uniform price
   (see [uniform-price-dissolves-the-uncontested-round](/decisions/uniform-price-dissolves-the-uncontested-round.md)).
   "Politely asking the one supplier" and "bidding war" are one mechanism with contention as
   the dial, which is why no separate request path exists or is needed.
4. **Consult** — no row in the menu for this gap: ask the model, at the edge of knowledge,
   exactly as [the-model-is-consulted-at-the-edge-of-knowledge](/decisions/the-model-is-consulted-at-the-edge-of-knowledge.md)
   reserved it. The empty menu is not a failure state; it is the Consulting member's
   invocation condition.

Each rung amortises the one above: intention amortises deliberation, the market amortises
negotiation, and consulting is priced at the rate the world genuinely surprises. This extends
[an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md)
by one level rather than amending it.

## The rule that makes rung 2 honest

**The market is about the resource, not the lever.** The test for direct actuation is not
"do I hold an actuator plumbed to my pot" — it is "does the DOSE come out of anything that is
not mine". A pot-local pump drawing from a shared barrel is a lever the agent owns on a
resource it does not, and opening it without a claim would take from the commons without
bidding — precisely what the market referees. So the Acquire walk
(see the menu, [#189](https://github.com/ShishkinDmitriy/agora/pull/189)) follows the LEVER
chain to the pot, and the Actuate premise must additionally follow the RESOURCE chain to the
source: `actuation:drawsFrom` a source no market offers as its lot. Two different walks,
because ownership of the pipe and ownership of what flows through it are different facts.

One hardware rig therefore admits three societies, all expressible with today's vocabulary
plus rung 2: pumps at the shared barrel (supplier hosts, plants bid — the shipped shape); a
pump per pot on per-pot bottles (self-watering agents, no market, Actuate rows); and a pump
per pot on the SHARED barrel — the most instructive — where every agent owns its lever and
still must buy the water, a winning claim authorising the agent's own pump to draw.

## Enforcement: possession is not authority

Asked immediately by the sovereign: N agents with their own pumps on another agent's tank —
what stops stealing? The answer is the founding split this architecture is built on
([trust-boundary](/decisions/trust-boundary.md),
[thin-trusted-infra](/decisions/thin-trusted-infra.md)): an agent HOSTS its pump and does not
COMMAND it. A dose happens only against a claim signed by the clearing — keys no agent holds,
which is why `create_keypair` lives in onboarding — and the verification runs in the PUMP'S
FIRMWARE, the bounded device, which mounts the society's public keys and nothing secret. A
malicious agent commanding its own pump is refused by its own hardware, because the pump is
loyal to the society's keys, not to whoever's box it sits in; loyalty is installed at flash
time, which is why the sovereign flashes. Around that core: the broker ACL narrows who can
speak to a command topic at all; the REA ledger plus dose confirmations plus the tank's own
level instrument make any theft that somehow happened VISIBLE and attributable (dispensed
minus sold is an auditable difference — theft here is evidence-producing, not merely hard);
and the adversarial setting has a physical mirror of the co-signature, a supplier-held gate
valve in series at the source, so a dose needs both parties' actuators to agree. What is
honestly open: revocation ([#28](https://github.com/ShishkinDmitriy/agora/issues/28),
[#29](https://github.com/ShishkinDmitriy/agora/issues/29)), and carrying the sim valves'
verification into the real pump firmware when the terrace actuator is built.

**And when the firmware is not yours?** Asked next, and the answer is not "keep hardware dumb"
but "never model loyalty you did not install" — which differ, derivably. A device nobody here
flashed is not dumb, it is UNKNOWN, and unknown is worse: a dumb relay is a known quantity
(does whatever its wire says, always), while a vendor's smart valve promises whatever its
vendor promised. So the honest classes are three — BOUNDED (sovereign-flashed, verifies
claims, auditable because its firmware is in this repository), DUMB (obeys its wire,
guaranteed nothing else), FOREIGN (someone else's promises, honestly modelled as dumb) — and
enforcement re-sorts by class: bounded keeps verification at the edge, which is
thin-trusted-infra's whole trajectory (dumb-everywhere would re-fatten the broker into the
single trusted enforcer, the exact centralisation that record relaxes); dumb retreats to the
choke points actually held — the ACL, the accounting, and the resource owner's own gate in
series at the source, which for a dumb actuator stops being paranoia and becomes the design.
The trust class is a device fact the graph can state and the posture a validation result, on
the pattern this month built three times over: a device with no sovereign firmware class is
dumb by absence, and a world whose scarce shared source is reachable through a dumb actuator
with no upstream gate should refuse — or state, out loud, that the broker alone enforces its
scarcity. Only the unstated version is dishonest. Deriving that check is part of the Actuate
issue's world-modelling, not a mechanism of its own.

# Seams left open

- **The Actuate rung is unimplemented** — no menu branch, no derivation granting a
  self-actuating agent its capability pair, no executor path for a dose that fulfils no
  claim (it still needs signing, confirmation and a ledger entry: an unconfirmed self-dose is
  not a delivered one either). Tracked as an issue; the trigger is the first world with an
  agent that holds both a stake and its own supplied lever — which the terrace build can
  produce the day a pump is plumbed per pot.
- **Source contestedness is derivable but not yet derived**: "a source no market offers" is a
  walk over `market:hosts` / `actuation:drawsFrom` that nothing performs yet. It belongs in
  the same menu branch.
- **The selection rule between Reflex and Consulting** stays where the parent record left it:
  the empty menu is the intended trigger, and wiring it is the Consulting member's business.
