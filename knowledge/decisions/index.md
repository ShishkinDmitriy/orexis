# Decisions

Architecture decisions, ADR-style: context, the choice, why, and — where it matters — the
*seam* deliberately left open for a later stage. Read these when you're about to change
something, to check you're not welding shut a planned extension.

**Each line below is the claim, not the argument.** The full abstract is the `description:` in
each record's frontmatter, and the reasoning is the record. An entry marked SUPERSEDED still
holds its reasoning; its mechanism has moved, and the record says where.

# Principles that cut across everything

* [the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md) - Wanting, committing and deciding are the kernel's: their stores were built for every agent while the code reading them was a grant.
* [the-society-is-named-for-its-appetite](/decisions/the-society-is-named-for-its-appetite.md) - The project is named Orexis — Aristotle's desire-that-moves-to-action — because the BDI mind is the kernel and the auction is a replaceable part.
* [control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md) - Nothing here controls a step: a cadence not a reading, a mandate not a belief, an affordance not an action.
* [agent-centric-epistemics](/decisions/agent-centric-epistemics.md) - Judgment, private data and initiative belong to the agent; infra is thin honest mechanism.
* [english-vs-formal](/decisions/english-vs-formal.md) - English for what is contested, RDF and SHACL for what is trusted.

# Trust, identity and isolation

* [trust-boundary](/decisions/trust-boundary.md) - Agents cite but never author facts, mint currency, or actuate. Three privileged powers stay in trusted infrastructure.
* [thin-trusted-infra](/decisions/thin-trusted-infra.md) - Relax those powers toward public functions and signed artifacts; only the currency ledger is irreducibly trusted.
* [trusted-agent-mode](/decisions/trusted-agent-mode.md) - The v1 posture: no gateway, each agent asserts its own current state as opinion, sensor access capability-gated.
* [authn-authz-capabilities](/decisions/authn-authz-capabilities.md) - Cert is who you are and is durable; a signed grant is what you may do now and is ephemeral.
* [where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md) - The world is TTL files and each agent holds its own store, so isolation is structural rather than enforced.
* [series-and-bus-isolation](/decisions/series-and-bus-isolation.md) - A bucket and scoped token per agent; broker credentials and ACL derived from the same wiring that derives capability.
* [the-sovereign-may-ask](/decisions/the-sovereign-may-ask.md) - One SPARQL question to one running agent over the world's bus. Disclosure, not access; read-only by construction.
* [belief-base-isolation](/decisions/belief-base-isolation.md) - SUPERSEDED — privacy by per-graph ACLs. The intent is stronger now; there is no shared store to be let into.
* [two-store-beliefs](/decisions/two-store-beliefs.md) - SUPERSEDED IN PART — a series store and a graph store, joined by URI and never federated. The split holds; Fuseki is gone.

# The mind — desire, intention, deliberation

* [the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) - SUPERSEDED IN PART — the modalities and their findings stand; their carrier moved from graph to store.
* [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) - A modality is a store with its own persistence; graphs inside carry only arrival. The desires store is read-only to the runtime.
* [a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md) - SUPERSEDED IN PART — the met-test is SHACL and force is severity; the desire itself became a node carrying the shape.
* [a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md) - The reflex steered to the aim while the planner scored from the centre; one measure now, aim-anchored, declared by the capability owning the reading.
* [a-desire-is-a-forest-of-derived-roots](/decisions/a-desire-is-a-forest-of-derived-roots.md) - A root desire per premise, decomposed per instance, property and side, materialised with its why; every level must name a consumer.
* [desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md) - SUPERSEDED IN PART — a region per property, intersected from every range that applies; urgency's anchor moved from the centre to the aim.
* [the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md) - The plant states the range it needs in the world; the agent's target is a pick inside it.
* [an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md) - The distinction belongs on the goal, not the lever: a claim raises a desire whose provenance says whose it is.
* [a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md) - A belief is a point chosen inside a range, not a constant; genesis wrote the first pick, not a bound.
* [self-review-is-a-capability](/decisions/self-review-is-a-capability.md) - Revising your own settings is one ability with two implementations. What grants it is latitude.
* [an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md) - BDI's third letter: a commitment to reduce a named gap by a named means, so a decision is made once.
* [the-ladder-of-means](/decisions/the-ladder-of-means.md) - Look, act with what is yours, buy what is not, ask what you do not know — each rung costlier and more social.
* [a-habit-is-a-compiled-deliberation](/decisions/a-habit-is-a-compiled-deliberation.md) - A stable environment lets deliberation compile into if-then policy, minted and retired by review on evidence.
* [the-model-is-consulted-at-the-edge-of-knowledge](/decisions/the-model-is-consulted-at-the-edge-of-knowledge.md) - The LLM is a teacher, not a decider in the loop: consulted only when no written-down plan connects a gap to a lever.
* [a-consulted-answer-is-a-premise](/decisions/a-consulted-answer-is-a-premise.md) - What comes back from a model must be premises rather than steps, so a model never authors an act.
* [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) - Classical planning lifted to RDF: menu rows are action schemas and the Reflex is a depth-1 planner.
* [a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md) - Effects run against the store, so step two never sees step one. Snapshot per plan and bind the hypothesis in.
* [a-lever-an-agent-cannot-pull-is-not-a-lever](/decisions/a-lever-an-agent-cannot-pull-is-not-a-lever.md) - Knowing becomes sensing's own want, repaired through the search; the Observe row exists only where the agent can ask.
* [an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md) - The plan's head is what the keeper writes, execution is one kernel road, and `ag:takenBy` links a row to the code that takes it.
* [an-action-is-one-node](/decisions/an-action-is-one-node.md) - Precondition, effect and taker are one `ag:Action` node in `actions.ttl`; chosen/honoured is a column, and four surfaces became one.
* [an-intention-stands-until-the-world-answers](/decisions/an-intention-stands-until-the-world-answers.md) - An Actuate stands from the command to its verdict, so the standing rule is the whole patience and the `absorbs` hook is gone.
* [the-action-is-the-kind](/decisions/the-action-is-the-kind.md) - `ag:Means` read by nothing; the action node is what a row carries and an intention commits to, and the five means are gone.
* [an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan](/decisions/an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan.md) - An ACT is a filled action with a window, execution's word; a STEP is its place in a plan; a claim commits to a Serving act.
* [auction-and-clearing-are-the-markets](/decisions/auction-and-clearing-are-the-markets.md) - `auction.py`, `clearing.py` and the market's types leave the kernel for the package; a claim embodies the kernel's commitment, which is what a valve fulfils.
* [sensing-owns-the-reading-pipeline](/decisions/sensing-owns-the-reading-pipeline.md) - Codec, pointer, scaling, the sensed writer, observations and `readings.rq` move to sensing; what is known is a choir hook.
* [self-is-bdi-and-wiring-is-the-packages](/decisions/self-is-bdi-and-wiring-is-the-packages.md) - `Self` keeps id, capabilities and whom it acts for; sensors, actuators and venues are loaded by their packages' own `wiring.py`.
* [the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md) - Sensing derives the stake and answers what a reading looks like; the kernel derives no want and keys nothing by property.
* [a-round-is-a-fact-and-offering-is-an-action](/decisions/a-round-is-a-fact-and-offering-is-an-action.md) - A round is a belief on both sides, Acquiring needs an open one, and Offering is an action — the host's two-step becomes a plan.
* [llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) - Thin BDI: the LLM drives deliberation, so the formal layer becomes load-bearing rather than optional.
* [deterministic-bid](/decisions/deterministic-bid.md) - The bid number is code; the LLM only produces the justification. Rhetoric cannot move the number.
* [there-is-no-bdi-ontology](/decisions/there-is-no-bdi-ontology.md) - FIPA, DOLCE, prov:Plan, WoT TD and hmas surveyed and refused: the mind crosses no trust boundary, and BDI's words are already ours.

# The market

* [the-market-has-no-governor](/decisions/the-market-has-no-governor.md) - Deficit opens rounds and structure names the convener; fairness is entry and public terms, never a referee.
* [a-market-arises-where-want-meets-supply](/decisions/a-market-arises-where-want-meets-supply.md) - Market existence is derived from plumbing, with one authored triple as consent: stating how you match is opening shop.
* [the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md) - A round is triggered by a band and sized by a host belief, so the host is blind to quantity until bids are in.
* [the-lot-states-its-good](/decisions/the-lot-states-its-good.md) - The good becomes a node, because one good has a valuation per kind of recipient and every denomination join closes through it.
* [bid-matching-is-a-capability](/decisions/bid-matching-is-a-capability.md) - Turning a lot and bids into an allocation is a family with interchangeable members, announced in the offer.
* [bid-matching-is-the-word](/decisions/bid-matching-is-the-word.md) - Matching covers the allocation rule and the payment rule; format over-claims and means two incompatible things.
* [uniform-price-dissolves-the-uncontested-round](/decisions/uniform-price-dissolves-the-uncontested-round.md) - Every winner pays the lowest accepted bid, so the reserve is a floor and the contested-or-not test disappears.
* [a-round-is-an-iteration-not-the-auction](/decisions/a-round-is-an-iteration-not-the-auction.md) - The round is one pass of bidding; the auction is what condenses and dissolves.
* [a-role-needs-something-to-be-a-role-in](/decisions/a-role-needs-something-to-be-a-role-in.md) - Market positions stay predicates: a role needs a context object, and an auction deliberately has none.
* [clearing-as-validator](/decisions/clearing-as-validator.md) - Clearing is a thin stake-free notary that checks a proposed trade and co-signs it. The host computes the match.
* [standalone-clearing](/decisions/standalone-clearing.md) - The structurally scarce side hosts; the clearing validator stays topology-invariant. Amended by the-market-has-no-governor.
* [strategic-supplier](/decisions/strategic-supplier.md) - The supplier is a genuine seller with costs and a reserve price, not a stake-free utility.
* [single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md) - One wallet for water and compute, so thinking costs and bounded rationality is priced in.
* [bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md) - Bids reflect current unmet need, which keeps multi-source decomposition possible.
* [settlement-speaks-rea](/decisions/settlement-speaks-rea.md) - Settlement is ordinary economic exchange, so REA's words are borrowed: a claim is a commitment, actuation the event.
* [a-contested-state-is-leased-not-bought](/decisions/a-contested-state-is-leased-not-bought.md) - An indivisible state is allocated as an interval of control. A market allocates between desires, never against a rule.
* [an-unconfirmed-dose-is-not-a-delivered-one](/decisions/an-unconfirmed-dose-is-not-a-delivered-one.md) - A dose is counted only when the valve confirms it, and never re-sent, because over-watering is irreversible.

# Knowledge, graphs and provenance

* [who-put-the-fact-there](/decisions/who-put-the-fact-there.md) - Public knowledge is graphs split by who put the fact there. A SELECT that names one reads only part, silently.
* [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md) - Entailments are materialised into the store at genesis, so shapes and the runtime cannot disagree about the vocabulary.
* [every-term-in-its-own-house](/decisions/every-term-in-its-own-house.md) - Five packages took namespaces of their own. A term is named seven ways, and a rename sees one of them.
* [the-kernel-names-no-package-word](/decisions/the-kernel-names-no-package-word.md) - Packages are optional, so the core depends on none of them in RDF either. Nine occurrences left, ordered by danger.
* [a-hook-is-a-term](/decisions/a-hook-is-a-term.md) - Every choir question is an `ag:Hook` declared by whoever owns it; modules answer by decorating with the term; undeclared terms are refused.
* [model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md) - The test for what an agent believes about the layers and itself; store what comes from outside, compute what the interpreter knows.
* [the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md) - Network, transport, translation, BRF, mind — sliced by representation; the cognitive layers partition only the mind, and a message is not an observation.
* [layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md) - Reactive, progression, deliberation — split by latency and interruptibility; the belief base is the interface; progression is BDI's own layer.
* [metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md) - Every package counts its own and answers `reports()`/`series()`; the choir is the registry; reporting is the sink; the kernel counts only the mind's.
* [the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md) - Reaching the society is a capability the fact of a bus grants; the transport's module holds the connection, the loop and the watchdog.
* [a-mandate-is-not-a-commitment](/decisions/a-mandate-is-not-a-commitment.md) - review:Commitment is renamed review:Mandate: REA's commitment is the claim and BDI's is an intention, so the governance thing takes the word everyone used.
* [one-word-for-one-relation](/decisions/one-word-for-one-relation.md) - A subclass axiom claims our term means more; where nothing checks the difference it is a synonym.
* [what-is-true-of-a-part-is-true-of-every-one-of-them](/decisions/what-is-true-of-a-part-is-true-of-every-one-of-them.md) - A class-level triple is punning. An owl:hasValue restriction is what reaches every instance.
* [a-volume-can-be-older-than-the-vocabulary](/decisions/a-volume-can-be-older-than-the-vocabulary.md) - Beliefs outlive the code that wrote them, so boot asks whether the vocabulary still declares what the store uses.
* [an-amendment-endows-what-it-grants](/decisions/an-amendment-endows-what-it-grants.md) - Never-held terms arrive with their structures; held terms stay the agent's whatever their value.

# Packages and layout

* [capability-packages](/decisions/capability-packages.md) - A package is one directory holding its own ontology, shapes, rules, code and namespace — found by looking, never listed.
* [one-tree-and-one-mechanic](/decisions/one-tree-and-one-mechanic.md) - One tree, `packages/<family>/<name>/`, with the family read off the path and declared nowhere.
* [a-package-owns-its-namespace](/decisions/a-package-owns-its-namespace.md) - Prefixes are read off the ontologies that declare them. A directory is a package, not a capability.
* [repository-layout](/decisions/repository-layout.md) - One convention across the Python trees, one distribution, and a packaging boundary replaced by a test and an import contract.
* [a-package-may-test-itself](/decisions/a-package-may-test-itself.md) - A package carries its own tests beside its code, and `testpaths` names both roots so neither is invisible.
* [telemetry-is-a-mandatory-capability](/decisions/telemetry-is-a-mandatory-capability.md) - Rule 2 asks only whether the how could differ, so a capability every agent holds is still one — and is not optional.
* [capability-modules](/decisions/capability-modules.md) - SUPERSEDED IN PART — what a capability is, and that it is derived rather than declared, still holds. Where the files live does not.

# Hardware, sensing and firmware

* [who-holds-the-clock](/decisions/who-holds-the-clock.md) - Sensing splits by who holds the clock: Polling, Subscribing, Listening. What was called Polling was Subscribing.
* [freshness-follows-the-cadence](/decisions/freshness-follows-the-cadence.md) - Staleness is relative to the interval a Subscribing agent chose, absolute for Listening. "I do not know" is not "I am fine".
* [an-observation-says-how-it-was-made](/decisions/an-observation-says-how-it-was-made.md) - A reading carries its procedure, so silence from a late board is distinguishable from a quiet one.
* [a-procedure-belongs-to-whatever-performs-it](/decisions/a-procedure-belongs-to-whatever-performs-it.md) - Each system implements what it can perform, and procedures distribute down the hosting chain.
* [a-reading-is-one-value-so-it-is-pointed-at](/decisions/a-reading-is-one-value-so-it-is-pointed-at.md) - Where a value sits in a shared payload is a JSON Pointer, which identifies exactly one value.
* [bytes-become-a-quantity-in-stages](/decisions/bytes-become-a-quantity-in-stages.md) - Codec, pointer and scaling are stages borne by the binding rather than by the agent; scaling is where a number gets its unit.
* [a-stream-is-a-thing](/decisions/a-stream-is-a-thing.md) - A channel is derived from the topics devices state, its IRI a function of that string; the codec is the stream's.
* [channel-is-the-word](/decisions/channel-is-the-word.md) - The per-topic node was channel and stream interchangeably; the T-Box declares mqtt:Channel, so the prose moved to the code's word.
* [the-wire-is-ours-and-it-has-two-levels](/decisions/the-wire-is-ours-and-it-has-two-levels.md) - A transport and an encoding vary independently: the credential is the connection's, the encoding is the stream's.
* [a-board-is-a-platform](/decisions/a-board-is-a-platform.md) - The board three sensors share is a sosa:Platform hosting its parts, and mc:carries was sosa:hosts all along.
* [a-board-says-what-it-can-honour](/decisions/a-board-says-what-it-can-honour.md) - A device states a frequency it can keep, so an agent cannot commit to a cadence its board would never honour.
* [the-vigil-costs-standing-not-looking](/decisions/the-vigil-costs-standing-not-looking.md) - One radio wake buys a million ULP looks, so the patrol period is free and the heartbeat is the whole battery.
* [firmware-repeats-rather-than-shares](/decisions/firmware-repeats-rather-than-shares.md) - A shared library is a shared reflash, and what looks duplicated is the mechanism while the meaning differs per board.
* [a-firmware-describes-itself](/decisions/a-firmware-describes-itself.md) - `firmware/<name>/ontology.ttl` is a T-Box source: the flashed image's own facts, entailed onto every typed board.
* [a-part-is-described-once-and-fitted-many-times](/decisions/a-part-is-described-once-and-fitted-many-times.md) - We ship a package for a model, so datasheet facts are stated on classes and reach devices by entailment.
* [a-species-is-described-once-and-planted-many-times](/decisions/a-species-is-described-once-and-planted-many-times.md) - A species is a model and the pots are units, so planting one is one triple.
* [their-descriptions-are-our-fixtures](/decisions/their-descriptions-are-our-fixtures.md) - W3C's own examples are vendored and measured: a deployment description needs no editing, a device description needs four facts.
* [pins-and-wires](/decisions/pins-and-wires.md) - A pin is metal, a role is abstract, and the wire is what people get wrong — which makes a rail fault refusable.
* [wokwi-drafts-it-the-world-ratifies-it](/decisions/wokwi-drafts-it-the-world-ratifies-it.md) - Importing a diagram drafts a stand and never becomes its source; bidirectional sync was refused, not deferred.
* [one-agent-many-sensors](/decisions/one-agent-many-sensors.md) - Three of four combinations work, measured rather than assumed. Both failures come from a second kind of sensor on one subject.
* [the-alarm-answers-to-the-last-report](/decisions/the-alarm-answers-to-the-last-report.md) - SUPERSEDED IN PART — the deviation limit measures from the last value that left the board. The anchor holds; the band half does not.
* [an-undelivered-crossing-is-a-lie-told-by-silence](/decisions/an-undelivered-crossing-is-a-lie-told-by-silence.md) - Silence means nothing crossed only while the board can speak; undelivered crossings are retained and flushed.
* [the-sentinel-alarms-on-movement](/decisions/the-sentinel-alarms-on-movement.md) - The heartbeat says where the value is and the ULP says that it moved; the operating range sizes the trigger rather than being watched.
* [two-owners-of-one-peripheral](/decisions/two-owners-of-one-peripheral.md) - Arduino held ADC1 and the ULP enable call returned success anyway, so the handover is now a sequence rather than a setting.
* [a-stand-in-reports-what-its-world-says-it-does](/decisions/a-stand-in-reports-what-its-world-says-it-does.md) - A simulated device reports a value per property at the pointers its world declares, each drifting in its own range.
* [a-panel-is-a-sensor-not-an-agent](/decisions/a-panel-is-a-sensor-not-an-agent.md) - A panel is keyed on the sensor, because a sensor observes one property and states one unit.
* [a-name-does-not-expire](/decisions/a-name-does-not-expire.md) - A DHCP lease is a fact with an expiry date. The world states a hostname, and no firmware code changed.

# Worlds, genesis and operations

* [genesis](/decisions/genesis.md) - Sovereign narrates, LLM drafts, sovereign ratifies, infra writes. Each output is a whole world; agents are born from it.
* [world-graph](/decisions/world-graph.md) - No config file: the world graph holds only topology; desire, limits, cadence and prices are each agent's private beliefs.
* [two-worlds-were-one](/decisions/two-worlds-were-one.md) - Two worlds differed by 45 lines with identical beliefs, so the one that needs no hardware stayed.
* [a-dead-session-is-resigned-not-endured](/decisions/a-dead-session-is-resigned-not-endured.md) - An agent cut off from its bus sends itself SIGTERM; the container's restart policy is the recovery.

# Gates and guards

* [a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md) - Four guards went green while checking nothing. A root conftest fails the run if a test executed no assert.
* [the-dictionary-names-its-terms](/decisions/the-dictionary-names-its-terms.md) - A domain page binds its word to the declared term in frontmatter, and a test holds the join; external vocabularies are vendored to check against.

# Direction

* [roadmap](/decisions/roadmap.md) - What v1 is, and the v2/v3 extensions each seam unlocks.
