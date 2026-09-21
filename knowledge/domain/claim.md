---
type: Domain Concept
title: Claim
description: The token you win in the auction — a co-signed, single-use commitment by the supplier for N litres, redeemed to actuate. A commitment in REA's sense and deliberately not a claim, because nothing here is delivered before it is settled.
---

# What it is

Since [a-claim-is-water-at-a-time](/decisions/a-claim-is-water-at-a-time.md) a claim is
water AT A TIME: the bid said when the water was wanted, the claim says from when it may be
presented (`market:usableFrom`) and until when (`market:usableUntil`), and the presenting is
what an instant-bound want places at its instant.

The auction result as an object. A **claim** is what you *win*: "bearer is owed N litres of
water from supplier S this auction." It is distinct from the **access grant** that statically
binds an agent to a device — the access grant is *granted* (at genesis), the claim is *won*
in a round, or issued on an ask the [host](/domain/host.md)'s stock covers with no round at all.
Held and not yet presented, it is what makes buying available and a tender done. See
[authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# Shape

A `Claim` is the kernel's [commitment](/domain/commitment.md) — the promised flow — with the
credit leg added; the fields below are that shape plus `debit`. What it is a commitment TO is
the host's Serving [act](/domain/act.md): this venue, so many litres, for this buyer, not after
`exp` — issued with the claim, held by the host, and the act the buyer's presentation asks it
to take. **The window is the act's**: `exp` is its `not_after` on the wire, the host's redeem
check reads it, and the buyer's Acquiring act is windowed the same way at the round's close.
`not_before` on the act is the placed instant — the planner's, for a plan found from a future
root — and the presenting is placed by the claim's own window (`orexis:readyAt`).

`sub` (who won), the supplier, `amount_l`, `debit` (the price), `auction_id`, `jti` (single-use),
`exp`. **Co-signed** by the **host** (`match_sig` — the seller offered it) and
**clearing** (`val_sig` — it passed validation). Concretely a JWT/JWS; v1 signs with Ed25519.

# Against the supplier, not a valve command

The claim is against the **supplier** (the resource owner), not a command to a specific
actuator. The holder redeems it with the supplier; the supplier maps *how much* (the claim)
+ *which valve* (its `{plant_id → valve}` map, keyed by `sub`) and drives it. The buyer never
names a valve. See [supplier](/domain/supplier.md) and [actuation](/domain/actuation.md).

# Redemption — spot vs futures

- **Spot (v1, since #132):** **held briefly, then presented** — win → hold until the winner's
  sensor is provably watching (the #135 cadence ack, or a bounded wait) → the holder presents
  the claim on the market's `redeemTopic` → actuate. Win and actuate decoupled already, not for
  temporal strategy but for **observability**: never spend a dose you cannot watch land. Before
  #132 the host redeemed on issue, which spent the dose before the winner could see it arrive.
- **Futures (v2):** the same held claim, held *longer* — any time until `exp`, the timing the
  agent's. Enables temporal strategy (water at night, wait for rain, hedge a forecast). The
  wire and the holding mechanism exist since #132; what futures adds is the horizon. See the
  futures item in [roadmap](/decisions/roadmap.md).

# Single-use

`jti` makes it single-use: the host holds issued claims by `jti` and pops each on
presentation, so one win cannot settle twice and only the winner it was issued to may present
it (the presenter is read off the topic segment the ACL lets it write). The held set is
in-process — a host that restarts forgets unpresented claims, which is the claim-ledger seam
the roadmap records.

# It expires, and the venue says when

`exp` is set at issue from the market's own `market:redeemWindowS`, a triple the source states
and the derived venue carries. Every claim from one round shares it: the window runs from the
moment the society allocated, so two winners are held for the same time and neither can be late
by an accident of loop order. A presentation after it is refused and the paper is dropped; on
the holder's side the claim is a graph holding until the window's end (#645), handed to nobody
past it and dropped by the one sweep, so no later tender is done by it; on the host's side the
debt lapses with its verdict, `market:lapsedAt` in the [obligation](/domain/obligation.md)
record — which reads differently from paid and differently again from never demanded.

The window has to comfortably exceed the longest a holder may wait before presenting, and that
is one full cycle of whatever cadence its sensing currently commands — dynamic, so no shape can
check it. State it long: a generous window costs a debt remembered slightly too long, a mean one
charges a buyer for water that never left the barrel.

What it is *for* is urgency. A region want's heat comes from the survival envelope, and an obligation has no
envelope — its room is time, so an obligation's urgency is the fraction of the window that has
run. That is why the deadline had to exist as data before obligations could drive acts; see
[an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md).

# The boundary, stated honestly (#144, #145)

Three layers, three adversaries, and the broker is no longer trusted for any of it where the
roster publishes keys:

- the **ACL** keeps other agents out — tomato cannot subscribe `claim/fern` or write
  `redeem/fern`. Defence in depth now, not the proof;
- the **winner's signature** (#144) keeps a forged presentation out — exercising the claim
  requires fern's private key, not fern's topic, so a compromised broker or misgenerated ACL
  moves no water, and every honoured presentation is non-repudiable;
- the **seal** (#145) keeps the bus itself out — the claim travels as an envelope only the
  winner can open, so a port mirror or a curious operator carries ciphertext with the money in
  it. The co-signature chain stays about the *actuation command*, unchanged.

Both interoperate with the pre-key era through the attested roster (`orexis:signingKey` /
`orexis:sealingKey` in the world, written by `orexis-keygen`): no published key, no demand — a world
onboarded before keygen learned agents behaves exactly as it always did.

# Why it exists even for immediate watering

Two roles, only one of which needs a held object:

- **Authorization** (always) — the co-signed proof that *this* actuation won the auction and
  cleared (the actuate boundary). Even spot routes through it.
- **Instrument** (futures) — a held, spendable commitment, and the case where it may genuinely
  become a *claim* in REA's sense; see below.

See [thin-trusted-infra](/decisions/thin-trusted-infra.md) and
[clearing-as-validator](/decisions/clearing-as-validator.md).

# A commitment, and deliberately not a claim

In the REA accounting ontology — standardised as ISO/IEC 15944-4 and expressed in RDF as
[ValueFlows](https://www.valueflo.ws/) — a claim is a **commitment**: *"a planned economic flow
that has been scheduled or promised by one agent to another agent."* The valve opening later is
the **economic event** that fulfils it, and the wallet debit is the reciprocal event.

A **claim** in that vocabulary is a different thing: what exists when a flow has happened and its
reciprocal has not — someone delivered and someone owes. **This project has none.** A claim
carries `amount_l` and `debit` together, both legs, neither performed, so there is no moment where
water has flowed and payment has not. That absence is a real property of the design rather than an
oversight: settlement here is atomic.

It stops being true if **futures** land — a claim held and spent later (see
[roadmap](/decisions/roadmap.md)) pulls delivery and payment apart in time, and a claim may become
a thing worth naming. See [settlement-speaks-rea](/decisions/settlement-speaks-rea.md).

# Held, by the keeper

Winning is not actuating: the claim is held until the bidder's watch is live, or until one
full cycle of the cadence in force has passed, and then presented — blind, in the second
case, because a dose delayed forever is worse than a dose unobserved. The wait is the
[keeper](/domain/intention.md)'s, and since #523 it is declared rather than built: the claim
arriving is a fact in the bidder's own graph (`market:Claim`, with when it was claimed and
when it was presented), Presenting is the second step of Acquiring's [method](/domain/method.md),
and its `orexis:readyWhen` says the watch must be live — or the host must have redeemed the
claim already — with the sensor's horizon as `orexis:lapsesAt`.
