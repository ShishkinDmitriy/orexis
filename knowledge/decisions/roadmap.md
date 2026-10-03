---
type: Decision
title: Roadmap — where Agent 0.2.0 goes next, by the issues that carry it
description: >-
  Direction, not a task list: the open chains of issues in the order each unlocks the next, and the
  parked extensions with the record whose seam opens each.
status: accepted
timestamp: 2026-10-03T00:00:00Z
---

# Where it stands

[Agent 0.2.0 replaced the kernel](/decisions/agent-0-2-0-replaced-the-kernel.md), and 0.1.0 was
retired whole. What the previous roadmap listed as ahead and is now behind:

- **BDI, with no model in the loop.** Desires derive wants, a budgeted search finds plans over
  possible worlds, and the executor walks intentions and holds each step to what it predicted. The
  LLM member 0.1.0 declared was never built, and the 0.2.0 tree has no seam reserved for one.
- **The domain is a plug-in.** Hanoi, the courier, the tower, climate, actuation and the market are
  documents under `domains/`, and no shipped code names one
  ([the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md)).
- **Bus privacy.** Per-agent credentials, ACLs derived from the wiring and a bucket per agent
  ([series-and-bus-isolation](/decisions/series-and-bus-isolation.md)), and every agent on the bus
  over mTLS. A board still authenticates with a password on the plain port (#81).
- **Planning in time, its first half.** One timeline whose clock may run fast, predictions that
  accumulate rates between happenings, and an imaginarium kept between passes with the present
  identified in it ([the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md)).

# Next, in order

1. **What is wrong before what is missing** — #849 (predictions blind to committed steps) and #462
   (a frozen probe reads fresh forever).
2. **Planning in time, its second half** — #596, an action with a duration, then #591, a plan as a
   partial order, then #593, a want over several scopes; #565 and #527 narrow and resume the
   search, and #486 names a world by its path.
3. **The world answers otherwise** — #522, several outcomes with a likelihood, and #781, a plan that
   worked lifted into a method the executor proves or forgets.
4. **Several agents contend** — #567, one dispatcher and two vans, then #568, right-of-way as a lot
   the market allocates.
5. **Operating it** — #47, a world run end to end from nothing; #839,
   #836, #860 and #838, what a world states about its installation and its wiring.
6. **The edge** — #865, #868, #81, #322, #323, #461, #328 and #25, the boards and their firmware.

# Parked, with the seam that unlocks each

- **Nested markets** — the supplier a buyer upstream, scarcity propagating down as price; opened by
  [strategic-supplier](/decisions/0.1.0/strategic-supplier.md) leaving cost a replaceable input.
- **Many sources** — many suppliers, reverse auctions, an exchange; opened by
  [standalone-clearing](/decisions/0.1.0/standalone-clearing.md) and
  [bids-as-unmet-demand](/decisions/0.1.0/bids-as-unmet-demand.md).
- **Decentralized decomposition** — local auctions coupled by price, with no global view; the
  thesis, of which sequential decomposition is the stepping-stone.
- **Self-organization** — a chair elected, rotated or borrowed holds procedural authority only
  ([trust-boundary](/decisions/0.1.0/trust-boundary.md),
  [thin-trusted-infra](/decisions/0.1.0/thin-trusted-infra.md)).
- **An open society** — naturalize and endow, currency minted rather than seized, reputation on
  identity.
- **A world drafted from narration** — the sovereign narrates, a draft is ratified, onboarding
  writes the rest; opened by [genesis](/decisions/genesis.md).
- **Futures** — partly here already: a claim is held and presented within its own window (#625),
  so winning and acting are decoupled. A forward venue distinct from the spot round is not, and
  its seam is the claim's expiry ([authn-authz-capabilities](/decisions/authn-authz-capabilities.md)).

# Working principle

Extract from the concrete. A seam is generalised when a second world pushes on it, and not before:
the hierarchy was found in the rules because the tower combined hanoi and the courier, not because
it was designed ahead of them.
