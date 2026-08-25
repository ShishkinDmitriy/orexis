# Domain

The shared contract — what each component is, what it's responsible for, and its
invariants. This is the layer agents read for context (in an LLM-heavy design, from the
T-Box). It describes the design; it is NOT the live sensed state.

# Agents (the tier with a stake)

* [agent](/domain/agent.md) - The general principal: certified identity, wallet, stake. Plant agent and supplier specialise it.
* [plant-agent](/domain/plant-agent.md) - A self-interested plant: desire, wallet, a stance of its own. Judges its own band, asserts its own readings.
* [supplier](/domain/supplier.md) - Strategic seller downstream, genuine buyer upstream, the barrel between. Actuates its own valves; cannot mint.
* [host](/domain/host.md) - Whoever convenes a venue and runs its rounds. A role a supplier or a dealer plays; which side hosts is structural, never measured.

* [sovereign](/domain/sovereign.md) - Whoever ratified a world. A role, not an identity, and outside the society: it may ask a running agent, never reach into one.

* [dealer](/domain/dealer.md) - An intermediary that buys from the N and sells to the M, holds stock and earns the spread. The stock decouples its two markets.

# Market

* [good](/domain/good.md) - What a lot is a quantity OF. One good has a valuation per kind of recipient, and every denomination join closes through it.
* [lot](/domain/lot.md) - What one auction sells — a quantity of the venue's good at a reserve, both the host's own beliefs, sized by nothing anyone needs.
* [market](/domain/market.md) - The standing structure — a resource, who supplies it, who consumes it, and the links between. The auction condenses inside it.
* [venue](/domain/venue.md) - One market, as a node in the graph — minted from stock plus consent, keyed by its source, so one owner with two goods holds two.
* [auction](/domain/auction.md) - The process, not a place: it condenses out of scarcity, announces terms, collects bids, matches, is co-signed, and dissolves.
* [round](/domain/round.md) - One pass of bidding inside an auction. Exactly one is built, so today the two coincide.
* [call](/domain/call.md) - A round is wanted on a venue because a participant said LOW — a want the host did not source, planned like any other.
* [bid matching](/domain/bid-matching.md) - A lot and a set of bids become an allocation with prices — an allocation rule and a payment rule together.
* [clearing](/domain/clearing.md) - A thin stake-free notary: checks a proposed trade and co-signs the claim. The host computes the match.
* [commitment](/domain/commitment.md) - REA's promised flow, as the kernel's shape: what a valve fulfils, what a claim embodies. Not BDI's, which is an intention.
* [claim](/domain/claim.md) - What you win — co-signed, single-use, held until the winner's watch is live, then presented on the redeem channel.
* [executor](/domain/executor.md) - The supplier's actuation arm: verifies the claim and drives its own valve, bounded by clearing and the device fail-safe.

# Ends

* [region](/domain/region.md) - The range a subject needs a property to stay inside, deduced by intersection. Beside it, the envelope outside which the subject ends.

* [aim](/domain/aim.md) - The point an agent picks inside its region. Its own, and a first pick rather than a bound — so constrain well, do not guess well.

* [pick](/domain/pick.md) - A point chosen inside room the agent did not choose. Unfalsifiable, so a want; the aim is one, the cadences and patience the rest.


* [urgency](/domain/urgency.md) - One scalar from 0 to 1 that makes unlike wants comparable. Several sources, one meaning; not knowing is maximal.

* [obligation](/domain/obligation.md) - A desire the agent did not source. Whom it may owe is topology; what it owes now is private runtime state.

* [desire](/domain/desire.md) - What an agent is trying to bring about, and the capability that deduces it. A stake and a duty are the same type on purpose.

* [root desire](/domain/root-desire.md) - A want quantified over a class, one per premise; the forest above the per-instance, per-property, per-side wants an agent pursues.

* [intention](/domain/intention.md) - A commitment to reduce a named gap by a named action, kept in a private ledger. Granted by a stake AND a lever.

* [deliberation](/domain/deliberation.md) - The whether: name the next move by building the world each lever would make and keeping the one worth reaching. One road.

* [action](/domain/action.md) - One way of acting as one node — and the kind of act itself: precondition, effect, taker. A package adds one node and one `take()`.
* [act](/domain/act.md) - An action filled in — lever, want, quantity, whom for, and a window. Execution's word: committed, taken, promised.
* [step](/domain/step.md) - Planning's word: an act at its place in a plan with what the search predicted. Only the head's act is committed.

* [affordance](/domain/affordance.md) - One row of what an agent could do now — an action whose precondition holds. Derived and never stored; whom it serves is a column.

* [lever](/domain/lever.md) - The INSTRUMENT an act goes through, always an instance. Its absence is what removes a row, with nothing edited.
* [link](/domain/link.md) - How an agent reaches its society: the kernel contract a transport implements. Not a driver, which reaches one device.

* [effect](/domain/effect.md) - What taking an action would make true: a package's SHACL rule, with its timing and the route by which anyone would learn it landed.

* [gap](/domain/gap.md) - The signed, normalised distance from what is sensed to what is wanted. A verdict, computed always and stored never; no reading yields no row.

* [imaginarium](/domain/imaginarium.md) - The store a plan thinks in: in memory for one plan, a graph per search node, required to be lost.

* [execution](/domain/execution.md) - Plan, commit the head as an intention, hand it to its actor. One road for every trigger; a standing step is taken, not re-decided.

* [actor](/domain/actor.md) - The module an affordance is linked to, through `ag:takenBy` stated by the package that ships the row. Takes a step; never decides one.

# Doing

* [actuation](/domain/actuation.md) - The power to touch the physical world, held by whoever owns the hardware. Bounded by a claim and by the device's own cap.

* [review](/domain/review.md) - An agent re-picking its own settings inside the room its world left it. Granted by latitude; a mandate whose ends meet grants nothing.

# Sensing

* [band](/domain/band.md) - One of three zones a region divides a property into. A verdict, not a measurement, and never stored.

* [observation](/domain/observation.md) - The node recording one act of observing. One per subject and property, and it replaces rather than accumulates.

* [reading](/domain/reading.md) - The value an observation carries, and the only fact in a belief base that is somebody else's word. It ages; it never expires.

* [channel](/domain/channel.md) - One named message flow on a bus, as a node — derived per distinct topic, discovered never authored, and the bearer of the encoding.
* [sensing](/domain/sensing.md) - Split by WHO HOLDS THE CLOCK: Polling, Subscribing, Listening. Either way the agent owns the freshness rule.

# Structure — how the project is put together

* [modality](/domain/modality.md) - What a fact asserts, as opposed to what it is about. The mind's axis: one class per modality, each owning its store.

* [capability](/domain/capability.md) - A named ability with interchangeable implementations. Granted by its own premise, deduced at genesis, and never hand-declared.

* [choir](/domain/choir.md) - The kernel asks every module, whoever holds an opinion answers, and the asker never learns who — provider's complement, and silence is not zero.

* [shape](/domain/shape.md) - SHACL, saying both "you may not" and "I want". Severity is the only difference, and the split is ours rather than the spec's.

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
