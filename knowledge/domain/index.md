# Domain

The shared contract — what each component is, what it's responsible for, and its
invariants. This is the layer agents read for context (in an LLM-heavy design, from the
T-Box). It describes the design; it is NOT the live sensed state.

# Agents (the tier with a stake)

* [agent](/domain/agent.md) - The general principal: certified identity, wallet, stake. Plant agent and supplier specialize it.
* [plant-agent](/domain/plant-agent.md) - A self-interested plant: desire, wallet, event-driven state machine, one LLM call for its stance; judges its own band, asserts its own `:sensed` data.
* [supplier](/domain/supplier.md) - Strategic seller that hosts the auction, and (as resource owner) actuates its own valves to fulfil vouchers. Cannot mint. In v2 buys upstream.

# Market

* [market](/domain/market.md) - A market is the standing structure — a resource, who can supply it, who can consume it, and the links between them; the auction is the process that condenses inside it and dissolves. Who hosts, who's in the cluster, and how participants know each other (attested topology).
* [auction](/domain/auction.md) - The process, not a place: it condenses out of scarcity, announces its terms, collects bids, matches, is co-signed by clearing, and dissolves. What it is made of (market, round, matching, clearing) and what it is not. Who convenes it is stated in v1 — the short-side principle is documented and unimplemented.
* [round](/domain/round.md) - One pass of bidding inside an auction, not the auction itself — the standard meaning from multiple-round designs. Exactly one is built, so today an auction has a single round and the two coincide; the iterative flow described is designed and unbuilt.
* [bid matching](/domain/bid-matching.md) - Turning a lot and a set of bids into a proposed allocation with prices — an allocation rule and a payment rule together. The host declares how it matches and every offer announces it; pay-as-bid rewards shading, uniform price rewards demand reduction. Deliberately narrower than an auction format, which also fixes how bidding proceeds; qualified because bare matching collides with matching a capability to a provider.
* [clearing](/domain/clearing.md) - Thin stake-free validator / public function (a notary): checks a proposed trade and co-signs the voucher. The host computes the match, not clearing.
* [voucher](/domain/voucher.md) - What you win: a co-signed, single-use claim on the supplier for N litres, redeemed to actuate (spot now, futures later).
* [executor](/domain/executor.md) - The supplier's actuation arm: verifies the voucher and drives its own valve, bounded by clearing + the device fail-safe.

# Ends

* [desire](/domain/desire.md) - What an agent is trying to bring about: one region per property its subject states a need in, plus the envelope outside which that subject ends. Deduced by intersecting every operating range that applies, never authored, and held in a graph found by type so a second source needs no code. The band and the urgency every other capability reads come from here — which is why an agent with no stake has neither.

# Perception

* [sensing](/domain/sensing.md) - Perception split by WHO HOLDS THE CLOCK: Polling (the agent asks each time — reserved), Subscribing (the agent states an interval, the device keeps it), Listening (the device announces). Either way the agent owns the freshness rule, and a bid must cite a reading it trusts.

# Genesis and structure

* [genesis-process](/domain/genesis-process.md) - The LLM-assisted session that turns a description into a living society: what must be elicited, what "consistent" means concretely, where opening beliefs come from, and why a world's KIND changes the operational ones but never the stake ones.
* [agent-metrics](/domain/agent-metrics.md) - What an agent says about itself: belief base size, seconds since a sensor last delivered, and the write failures that were previously caught and only logged. In the kernel because every agent has a belief base whatever it composed; the interval is a belief whose absence means it reports nothing.
* [onboarding](/domain/onboarding.md) - The phase between genesis and a running society: a bucket and token per agent, a bus credential and ACL per principal, a compose file — every one derived from the wiring rather than decided, which is why it is one command and safe to re-run. Not birth, and the difference is the point.
* [world](/domain/world.md) - What a ratified world is made of (public topology + one private beliefs file per agent), the three rules for authoring one, and what genesis DERIVES rather than accepts. Several worlds coexist; which one is seeded decides what each agent becomes.

# Rules and resources

* [constitution](/domain/constitution.md) - Hard, non-negotiable constraints enforced by code, not persuasion.
* [wallet](/domain/wallet.md) - The single budget; how bids and metabolic cost are computed and debited.
* [belief-base](/domain/belief-base.md) - One belief base per agent, not one shared store: named-graph layout, SOSA shape, provenance, and why isolation is now structural rather than enforced.
* [gateway](/domain/gateway.md) - Decommissioned in v1 (trusted-agent mode): the measurement-witness role, folded into the self-asserting plant edge; returns as a signing sensor only for an adversarial society.
