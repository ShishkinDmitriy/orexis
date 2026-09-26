# Domain

The shared contract — what each component is, what it's responsible for, and its
invariants. This is the layer agents read for context (in an LLM-heavy design, from the
T-Box). It describes the design; it is NOT the live sensed state.

# Agents (the tier with a region want)

* [agent](/domain/kernel/agent.md) - The general principal: certified identity, wallet, region want. Plant agent and supplier specialise it.
* [supplier](/domain/market/supplier.md) - Strategic seller downstream, genuine buyer upstream, the barrel between. Actuates its own valves; cannot mint.
* [host](/domain/market/host.md) - Whoever convenes a venue and runs its rounds. A role a supplier or a dealer plays; which side hosts is structural, never measured.

* [sovereign](/domain/kernel/sovereign.md) - Whoever ratified a world. A role, not an identity, and outside the society: it may ask a running agent, never reach into one.


# Market

* [market](/domain/market/market.md) - The standing structure — who supplies a resource, who consumes it. In 0.2.0 a domain of files: documents, rules and actions.
* [auction](/domain/market/auction.md) - The process, not a place: it condenses out of scarcity, announces terms, collects bids, matches, is co-signed, and dissolves.
* [round](/domain/market/round.md) - One pass of bidding inside an auction. Exactly one is built, so today the two coincide.
* [call](/domain/market/call.md) - A round is wanted on a venue because a participant said LOW — a want the host did not source, planned like any other.
* [claim](/domain/market/claim.md) - What you win — co-signed, single-use, held until the winner's watch is live, then presented on the redeem channel.
* [actuation](/domain/actuation/actuation.md) - The supplier's actuation arm: verifies the claim and drives its own valve, bounded by clearing and the device fail-safe.

# Ends

* [region](/domain/sensing/region.md) - The range a subject needs a property to stay inside, deduced by intersection. Beside it, the envelope outside which the subject ends.

* [budget](/domain/planning/budget.md) - How many worlds one pass may imagine: the sovereign's pick in the agent's beliefs, bounded by shape, defaulted by the engine. Not a depth.






* [desire](/domain/planning/desire.md) - Two kinds: a desire stands and is never pursued; a want is deduced from one when the world makes it bite, and carries a period.


* [intention](/domain/execution/intention.md) - A commitment to reduce a named gap by a named action, kept in a private ledger. Granted by a region want AND an action.

* [deliberation](/domain/belief/deliberator.md) - In 0.1.0 the whether, the search; in 0.2.0 the belief package's pass, revising what was written within a budget and continuing a cut.


# Means — actions, steps, and what taking one comes to

* [action](/domain/kernel/action.md) - One way of acting as one node — and the kind of act itself: precondition, effect, implementation.
* [step](/domain/execution/step.md) - One action filled in: its parameters bound, whom it serves. A world's are derived; a plan's are written down.
* [plan](/domain/planning/plan.md) - What one pass returns for one want: steps in order, an outcome, a cost, the candidate it came through. Never executed, never stored.
* [precondition](/domain/planning/precondition.md) - The facts a step's rule read, instantiated; a plan's is their regression; checked by asking the present, never by re-running the rule.
* [act](/domain/execution/act.md) - The record that a step was taken: which step, when, whether anyone took it. History, and only history.

* [footprint](/domain/planning/footprint.md) - What one text reads and what it writes, as predicates, taken from the text; unreadable is anything, and only a VALUES block bounds a variable predicate.
* [scope](/domain/planning/scope.md) - Predicates joined wherever one action or derivation touches both; wants in different scopes cannot contradict.

* [implementation](/domain/execution/implementation.md) - How an action is carried out when a step is taken: operations grouped by order, sized from the present, never read by a search.
* [operation](/domain/execution/operation.md) - One thing taking a step does — a command, a saying, or the fictive write. Not an act, which is the record.
* [speech](/domain/speech/speech.md) - A peer's word is a document: heard where it is state and replaces only a peer's word, and what the agent said, believed as said.
* [transport](/domain/transport/transport.md) - How an agent reaches its society: a capability the bus grants, holding the connection and three choir hooks. Not a driver.

* [effect](/domain/planning/effect.md) - What taking an action would make true and false: rules in SHACL's shape, grouped by order, run on a possible world, deletes included.


* [imaginarium](/domain/planning/imaginarium.md) - The store a plan thinks in: a graph per search node, kept as diffs across passes, re-rooted where the present is a kept world.
* [cone](/domain/planning/cone.md) - The tree of possible worlds a pass builds under the present for one want; kept across passes, re-rooted where the present is one of them.

* [executor](/domain/execution/executor.md) - Plan, commit the head as an intention, hand it to its actor. One path for every trigger; a standing step is taken, not re-decided.


# Levels — what a step comes to beneath it

* [bridge](/domain/planning/bridge.md) - A rule concluding one domain's fact from another's, authored by the world combining them; run forwards over beliefs, backwards to refine a step.
* [refinement](/domain/planning/refinement.md) - A step whose predicted fact a bridge concludes is kept below, as a want whose met-test is the landing world regressed.

# Doing

* [actuation](/domain/actuation/actuation.md) - The power to touch the physical world, held by whoever owns the hardware. Bounded by a claim and by the device's own cap.


# Sensing

* [prediction](/domain/prediction/prediction.md) - What an agent expects at a horizon: in 0.2.0 a predicted observation per stretch between the instants the reading changes range.

* [observation](/domain/sensing/observation.md) - The node recording one act of observing. One per subject and property, and it replaces rather than accumulates.

* [reading](/domain/sensing/reading.md) - The value an observation carries, and the only fact in a belief base that is somebody else's word. It ages; it never expires.

* [sensing](/domain/sensing/sensing.md) - Split by who holds the clock. In 0.2.0 the translation row: bytes to an observation, predictions of when it changes range, no transport word.

# Structure — how the project is put together

* [modality](/domain/kernel/modality.md) - What a fact asserts, as opposed to what it is about. The mind's axis: one class per modality, each owning its store.



* [shape](/domain/planning/shape.md) - SHACL, saying both "you may not" and "I want". Severity is the only difference, and the split is ours rather than the spec's.

* [package](/domain/kernel/package.md) - The one unit the loader knows: one directory, five optional files, the family read off the path, PROVIDES as the only registration.

# Genesis and worlds

* [onboarding](/domain/onboarding/onboarding.md) - The phase between genesis and a running society: a bucket, a token, a credential, an ACL, a compose file — all derived.
* [world](/domain/kernel/world.md) - What a ratified world is made of, the rules for authoring one, and what genesis DERIVES rather than accepts.
* [domain](/domain/kernel/domain.md) - What several worlds pose: its words, its actions, what its words mean when wanted. A world imports it.

# Rules and resources

* [belief-base](/domain/belief/belief-base.md) - One belief base per agent, not one shared store: named-graph layout, SOSA shape, provenance, structural isolation.
* [planner](/domain/planning/planner.md) - Runs planning: a bounded search over simulated worlds, writing one possible world per node.
* [runtime](/domain/kernel/runtime.md) - The 0.2.0 process: boots a world from its files, plans and walks pass by pass, stops when every desire is met.
* [inference](/domain/kernel/inference.md) - Materialises what the vocabulary entails, so both engines read one graph.
* [revision](/domain/belief/revision.md) - A belief derived from beliefs by SHACL 1.2's rules, adopted as they stand, into a graph of the source's own, on the present only.
