# Domain

The shared contract — what each component is, what it's responsible for, and its
invariants. This is the layer agents read for context (in an LLM-heavy design, from the
T-Box). It describes the design; it is NOT the live sensed state.

# Agents (the tier with a stake)

* [agent](/domain/agent.md) - The general principal: certified identity, wallet, stake. Plant agent and supplier specialise it.
* [plant-agent](/domain/plant-agent.md) - A self-interested plant: desire, wallet, a stance of its own. Judges its own band, asserts its own readings.
* [supplier](/domain/supplier.md) - Strategic seller downstream, genuine buyer upstream, the barrel between. Actuates its own valves; cannot mint.
* [dealer](/domain/dealer.md) - An intermediary that buys from the N and sells to the M, holds stock and earns the spread. The stock decouples its two markets.

# Market

* [good](/domain/good.md) - What a lot is a quantity OF. One good has a valuation per kind of recipient, and every denomination join closes through it.
* [market](/domain/market.md) - The standing structure — a resource, who supplies it, who consumes it, and the links between. The auction condenses inside it.
* [auction](/domain/auction.md) - The process, not a place: it condenses out of scarcity, announces terms, collects bids, matches, is co-signed, and dissolves.
* [round](/domain/round.md) - One pass of bidding inside an auction. Exactly one is built, so today the two coincide.
* [bid matching](/domain/bid-matching.md) - A lot and a set of bids become an allocation with prices — an allocation rule and a payment rule together.
* [clearing](/domain/clearing.md) - A thin stake-free notary: checks a proposed trade and co-signs the claim. The host computes the match.
* [claim](/domain/claim.md) - What you win — co-signed, single-use, held until the winner's watch is live, then presented on the redeem channel.
* [executor](/domain/executor.md) - The supplier's actuation arm: verifies the claim and drives its own valve, bounded by clearing and the device fail-safe.

# Ends

* [desire](/domain/desire.md) - One region per property its subject states a need in, plus the envelope outside which that subject ends. Deduced, never authored.

* [intention](/domain/intention.md) - A commitment to reduce a named gap by a named means, kept in a private ledger. Granted by a stake AND a lever.

* [deliberation](/domain/deliberation.md) - The whether, extracted: given the gap and what stands, name the next move. Three members, two of them built.

* [affordance](/domain/affordance.md) - One row of what an agent could do. Derived and never stored, contributed per package, and the reason chaining needs no preconditions.

* [imaginarium](/domain/imaginarium.md) - The store a plan thinks in: in memory for one plan, a graph per search node, required to be lost.

# Sensing

* [sensing](/domain/sensing.md) - Split by WHO HOLDS THE CLOCK: Polling, Subscribing, Listening. Either way the agent owns the freshness rule.

# Structure — how the project is put together

* [package](/domain/package.md) - The one unit the loader knows: one directory, five optional files, the family read off the path, PROVIDES as the only registration.
* [model-and-unit](/domain/model-and-unit.md) - A part, a species and a firmware are MODELS; the things in a world are UNITS, and inherit the model's facts by entailment.

# Genesis and worlds

* [genesis-process](/domain/genesis-process.md) - The LLM-assisted session that turns a description into a living society: what is elicited, and what a world's kind changes.
* [agent-metrics](/domain/agent-metrics.md) - What an agent says about itself: belief base size, seconds since a sensor delivered, and the write failures.
* [onboarding](/domain/onboarding.md) - The phase between genesis and a running society: a bucket, a token, a credential, an ACL, a compose file — all derived.
* [world](/domain/world.md) - What a ratified world is made of, the rules for authoring one, and what genesis DERIVES rather than accepts.

# Rules and resources

* [constitution](/domain/constitution.md) - Hard, non-negotiable constraints enforced by code, not persuasion.
* [wallet](/domain/wallet.md) - The single budget for water and thinking. Solvency is checked against a balance the bidder self-reports; the ledger, the allowance and metering are designed, not built.
* [belief-base](/domain/belief-base.md) - One belief base per agent, not one shared store: named-graph layout, SOSA shape, provenance, structural isolation.
* [gateway](/domain/gateway.md) - Decommissioned in v1: the measurement-witness role, folded into the self-asserting plant edge.
