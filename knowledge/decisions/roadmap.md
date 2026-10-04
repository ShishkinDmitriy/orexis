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
  LLM member 0.1.0 declared was never built, and the 0.2.0 tree has no seam reserved for one
  inside the mind; a model stands outside it, in two places that read and never write: the present,
  what an agent accounts of itself for its sovereign over chat
  ([an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md)),
  and the season, the agent's series read back as reflection and offered as a proposal
  ([reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md)).
- **The domain is a plug-in.** Hanoi, the courier, the tower, climate, actuation and the market are
  documents under `domains/`, and no shipped code names one
  ([the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md)).
- **Bus privacy.** Per-agent credentials, ACLs derived from the wiring and a bucket per agent
  ([series-and-bus-isolation](/decisions/series-and-bus-isolation.md)), and every agent on the bus
  over mTLS. A board still authenticates with a password on the plain port (#81).
- **Planning in time, its first half.** One timeline whose clock may run fast, predictions that
  accumulate rates between happenings and see the steps the agent is committed to
  ([committed-step](/domain/execution/committed-step.md), #849), and an imaginarium kept between passes
  with the present identified in it ([the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md)).

# Next, in order

1. **What is wrong before what is missing** — nothing known is wrong today: a frozen probe is said
   stuck (#462, done; the detectors it listed and did not build are seams in
   [stuck](/domain/sensing/stuck.md)), and a world runs end to end from nothing on demand (#47, done).
2. **Planning in time, its second half** — #596, an action with a duration, down to its two unticked
   lines, a landing straddling a boundary and ranking by lateness. A plan as a partial order and a
   want over several scopes are seams, not issues, until a world pushes on them
   ([a-landing-is-a-band-and-a-world-holds-over-a-period](/decisions/a-landing-is-a-band-and-a-world-holds-over-a-period.md),
   [a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md)); the rest of
   the chain — narrowing, resuming and identifying the present, a world named by a mint number — is
   done.
3. **The world answers otherwise** — #522, several outcomes with a likelihood, and #781, a plan that
   worked lifted into a method the executor proves or forgets.
4. **Several agents contend** — #567, one dispatcher and two vans: the world and its measurement are
   in (`world/dispatcher/`), and the mechanism is decided and not built — a desire bounds the search
   and a plan found is the ground of the next, the derived want refused
   ([a-desire-bounds-the-search-and-a-plan-found-is-the-ground-of-the-next](/decisions/a-desire-bounds-the-search-and-a-plan-found-is-the-ground-of-the-next.md));
   the courier's landing band, the bound, the plan laid as predictions and the fictive committed
   step's prediction are its debts; then #568, right-of-way as a lot the market allocates.
5. **Operating it** — #839, #836, #860 and #838, what a world states about its installation and
   its wiring; and the sovereign over chat — an agent's account of itself, the gateway that relays
   it and the model that phrases a free question, then #862's recalibration walked with a person
   ([an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md)).
6. **The edge** — #865, #868, #322, #323, #461, #328 and #25, the boards and their firmware.

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
- **Reflection** — the agent's season read back from its series and offered to the sovereign as a
  proposal; opened by
  [reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md),
  whose first tool is the gap it emits.
- **Futures** — partly here already: a claim is held and presented within its own window (#625),
  so winning and acting are decoupled. A forward venue distinct from the spot round is not, and
  its seam is the claim's expiry ([authn-authz-capabilities](/decisions/authn-authz-capabilities.md)).

# Working principle

Extract from the concrete. A seam is generalised when a second world pushes on it, and not before:
the hierarchy was found in the rules because the tower combined hanoi and the courier, not because
it was designed ahead of them.
