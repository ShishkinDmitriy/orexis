# Domain

The shared contract — what each component is, what it's responsible for, and its
invariants. This is the layer agents read for context (in an LLM-heavy design, from the
T-Box). It describes the design; it is NOT the live sensed state.

# Agents (the tier with a stake)

* [agent](/domain/agent.md) - The general principal: certified identity, wallet, stake. Plant agent and supplier specialize it.
* [plant-agent](/domain/plant-agent.md) - A self-interested plant: desire, wallet, event-driven state machine, one LLM call for its stance; judges its own band, asserts its own `:sensed` data.
* [supplier](/domain/supplier.md) - Strategic seller that hosts the auction, and (as resource owner) actuates its own valves to fulfil vouchers. Cannot mint. In v2 buys upstream.

# Market

* [market](/domain/market.md) - How an auction condenses out of scarcity, who hosts, who's in the cluster, and how participants know each other (attested topology).
* [round](/domain/round.md) - The auction round: how a situation opens, iterates, and clears.
* [clearing](/domain/clearing.md) - Thin stake-free validator / public function (a notary): checks a proposed trade and co-signs the voucher. The host computes the match, not clearing.
* [voucher](/domain/voucher.md) - What you win: a co-signed, single-use claim on the supplier for N litres, redeemed to actuate (spot now, futures later).
* [executor](/domain/executor.md) - The supplier's actuation arm: verifies the voucher and drives its own valve, bounded by clearing + the device fail-safe.

# Perception

* [sensing](/domain/sensing.md) - Perception split by WHO HOLDS THE CLOCK: Polling (the agent asks each time — reserved), Subscribing (the agent states an interval, the device keeps it), Listening (the device announces). Either way the agent owns the freshness rule, and a bid must cite a reading it trusts.

# Genesis and structure

* [genesis-process](/domain/genesis-process.md) - The LLM-assisted session that turns a description into a living society: what must be elicited, what "consistent" means concretely, where opening beliefs come from, and why a world's KIND changes the operational ones but never the stake ones.
* [onboarding](/domain/onboarding.md) - The phase between genesis and a running society: a bucket and token per agent, a bus credential and ACL per principal, a compose file — every one derived from the wiring rather than decided, which is why it is one command and safe to re-run. Not birth, and the difference is the point.
* [world](/domain/world.md) - What a ratified world is made of (public topology + one private beliefs file per agent), the three rules for authoring one, and what genesis DERIVES rather than accepts. Several worlds coexist; which one is seeded decides what each agent becomes.

# Rules and resources

* [constitution](/domain/constitution.md) - Hard, non-negotiable constraints enforced by code, not persuasion.
* [wallet](/domain/wallet.md) - The single budget; how bids and metabolic cost are computed and debited.
* [belief-base](/domain/belief-base.md) - One belief base per agent, not one shared store: named-graph layout, SOSA shape, provenance, and why isolation is now structural rather than enforced.
* [gateway](/domain/gateway.md) - Decommissioned in v1 (trusted-agent mode): the measurement-witness role, folded into the self-asserting plant edge; returns as a signing sensor only for an adversarial society.
