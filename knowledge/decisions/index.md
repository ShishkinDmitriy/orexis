# Decisions

Architecture decisions, ADR-style: context, the choice, why, and — where it matters — the
*seam* deliberately left open for a later stage. Read these when you're about to change
something, to check you're not welding shut a planned extension.

**Each line below is the claim, not the argument.** The full abstract is the `description:` in
each record's frontmatter, and the reasoning is the record. An entry marked SUPERSEDED still
holds its reasoning; its mechanism has moved, and the record says where.

## Start here

* [agent-0-2-0-replaced-the-kernel](/decisions/agent-0-2-0-replaced-the-kernel.md) - 0.2.0 was built beside 0.1.0 and switched to whole; 0.1.0's records are [history](/decisions/0.1.0/index.md).
* [the-knowledge-is-filed-like-the-code](/decisions/the-knowledge-is-filed-like-the-code.md) - Pages filed by owning package and gated to live terms; a record stays current while something current cites it.

These are the records that still bind the code; 0.1.0's are [filed apart](/decisions/0.1.0/index.md).
A path through, for someone new:
[the-society-is-named-for-its-appetite](/decisions/the-society-is-named-for-its-appetite.md) for what
the project is, [agent-0-2-0-replaced-the-kernel](/decisions/agent-0-2-0-replaced-the-kernel.md) for
the kernel it runs,
[control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md) and
[model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md),
which between them decide most arguments, then
[a-want-is-judged-by-its-met-test-and-nothing-else](/decisions/a-want-is-judged-by-its-met-test-and-nothing-else.md)
for what an agent wants and [an-action-takes-parameters](/decisions/an-action-takes-parameters.md) for
what it does about it. **Going to change something?** Find the section it lives in below and read
that section whole — the seams are what you are checking for.

# Principles that cut across everything

The handful of sentences the rest of the bundle keeps appealing to. If you read nothing else, read these.

* [the-society-is-named-for-its-appetite](/decisions/the-society-is-named-for-its-appetite.md) - The project is named Orexis — Aristotle's desire-that-moves-to-action — because the BDI mind is the kernel and the auction is a replaceable part.
* [control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md) - Nothing here controls a step: a cadence not a reading, a mandate not a belief, an affordance not an action.
* [model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md) - The test for what an agent believes about the layers and itself; store what comes from outside, compute what the interpreter knows.
* [layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md) - Reactive, progression, deliberation — split by latency and interruptibility; the belief base is the interface; progression is BDI's own layer.
* [the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md) - Network, transport, translation, BRF, mind — sliced by representation; the cognitive layers partition only the mind, and a message is not an observation.
* [agent-centric-epistemics](/decisions/agent-centric-epistemics.md) - Judgment, private data and initiative belong to the agent; infra is thin honest mechanism.

# Trust, identity and isolation

Who may author what, and why isolation here is structural rather than enforced.

* [trusted-agent-mode](/decisions/trusted-agent-mode.md) - The v1 posture: no gateway, each agent asserts its own current state as opinion, sensor access capability-gated.
* [authn-authz-capabilities](/decisions/authn-authz-capabilities.md) - Cert is who you are and is durable; a signed grant is what you may do now and is ephemeral.
* [where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md) - The world is TTL files and each agent holds its own store, so isolation is structural rather than enforced.
* [series-and-bus-isolation](/decisions/series-and-bus-isolation.md) - A bucket and scoped token per agent; broker credentials and ACL derived from the same wiring that derives capability.

# The mind — what an agent wants

Desire: where a want comes from, what shape it has, and who is allowed to change it.

* [a-store-is-a-modality](/decisions/a-store-is-a-modality.md) - A modality is a store with its own persistence; graphs inside carry only arrival. The desires store is read-only to the runtime.
* [a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md) - SUPERSEDED IN PART — the met-test is SHACL and force is severity; the desire itself became a node carrying the shape.
* [a-want-is-judged-by-its-met-test-and-nothing-else](/decisions/a-want-is-judged-by-its-met-test-and-nothing-else.md) - Three things were called urgency; all three are gone, and a want's met-test is the one judgment left.
* [a-parcel-astray-is-a-want-of-its-own](/decisions/a-parcel-astray-is-a-want-of-its-own.md) - A shape over instances says each block is about `sh:this`, or two parcels are one want searched over the product.

# The mind — intention, act and execution

What happens to a decision — committed as an intention, carried out by whoever the T-Box says takes it.

* [an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md) - BDI's third letter: a commitment to reduce a named gap by a named means, so a decision is made once.
* [the-hierarchy-is-found-in-the-rules](/decisions/the-hierarchy-is-found-in-the-rules.md) - Combining two domains is enough: bridge rules, run backwards at a step, keep it below. Refused: per-action bridges, rules in the search.
* [an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md) - The plan's head is what the keeper writes, execution is one kernel path, and `orexis:takenBy` links a row to the code that takes it.
* [an-action-takes-parameters](/decisions/an-action-takes-parameters.md) - An action declares what it is filled with; the kernel carries opaque pairs and names no column.
* [the-action-is-the-kind](/decisions/the-action-is-the-kind.md) - `orexis:Means` read by nothing; the action node is what a row carries and an intention commits to, and the five means are gone.

# The mind — deliberation and the model

The search itself, and the two places a language model is allowed near it.

* [a-row-is-a-step](/decisions/a-row-is-a-step.md) - An affordance and a step were one shape in two classes; the service between the collections was a loop.
* [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) - Classical planning lifted to RDF: menu rows are action schemas and the Reflex is a depth-1 planner.
* [a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md) - Effects run against the store, so step two never sees step one. Snapshot per plan and bind the hypothesis in.
* [a-rule-does-not-say-which-world-it-reads](/decisions/a-rule-does-not-say-which-world-it-reads.md) - The door is told which world; naming it was one package claiming what every other package's actions can change. Costs nothing measurable.
* [a-node-holds-one-world](/decisions/a-node-holds-one-world.md) - The flat rdflib copy per search node is gone; a union of deltas cannot express retraction.
* [the-mutable-slice-was-narrowed-and-not-taken](/decisions/the-mutable-slice-was-narrowed-and-not-taken.md) - Shrinking what a fork copies works and buys nothing; the fork is 0.1% of a pass. Built as PR #664 and refused.
* [the-judge-speaks-rust](/decisions/the-judge-speaks-rust.md) - The SHACL judge is rudof behind one door, its two gaps closed on our side; pySHACL stays only as a gate.
* [the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md) - Tower of Hanoi: an ontology, one move action, no Python — the optimal solution is the cheapest achiever.
* [deliberation-is-on-triples-and-a-number-is-not-special](/decisions/deliberation-is-on-triples-and-a-number-is-not-special.md) - The core compares triples and interprets no literal; numbers, ranges or classes are the domain's choice; progression sizes the act.

# The mind — time and prediction

Time in the search: an instant, a stretch, a graph holding during a period, a prediction, and the clock the world keeps.

* [the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md) - The future is a tree of diffs under the observed present; execution identifies which child the present is in, never asserts one.
* [a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md) - A class is timeless; the stretch a saying holds during is the graph's, said once and read at the door. The forecast first.
* [a-reading-late-is-not-a-reading-missing](/decisions/a-reading-late-is-not-a-reading-missing.md) - An observation holds a cadence past its due, so a late reading leaves no hole in the present; its successor still replaces it on arrival.
* [one-catalogue-describes-every-graph-and-itself](/decisions/one-catalogue-describes-every-graph-and-itself.md) - One graph, the catalogue, says what every graph is, whose, how it arrived and when it holds, itself included, so no reader names it.
* [a-reader-states-the-kinds-it-reads](/decisions/a-reader-states-the-kinds-it-reads.md) - A query is handed its graphs; a reader asks by kind and instant; every row says every kind; the store decides nothing.
* [a-root-holds-always-and-an-outdated-graph-is-dropped](/decisions/a-root-holds-always-and-an-outdated-graph-is-dropped.md) - A root is authored at genesis into a graph with no period; everything sourced at a time has one, and one sweep drops the outdated.
* [the-agent-keeps-one-timeline-and-its-clock-may-run-fast](/decisions/the-agent-keeps-one-timeline-and-its-clock-may-run-fast.md) - One timeline for every instant and stretch; a compressed world paces the runtime's clock, and the mind never learns a unit.
* [the-drift-is-sensings-and-its-result-is-predictions](/decisions/the-drift-is-sensings-and-its-result-is-predictions.md) - Sensing runs every drift and writes predictions, graphs holding during windows typed with bands; the core reads them and runs no rule.
* [planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md) - A plan is published once and adopted by reference; a package owns its signals; the mind starts itself; an intention may end early.
* [a-package-starts-itself](/decisions/a-package-starts-itself.md) - The runtime is a lifecycle container: each package starts itself by jobs, kinds heard and timers; one thread runs them; packages meet at the store.
* [metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md) - Every signal carries an event its package declares, marking what is reported; metrics and history parts hear every signal, and nothing imports them.
* [an-observation-is-concluded-from-the-number-a-sensor-gave](/decisions/an-observation-is-concluded-from-the-number-a-sensor-gave.md) - Sensing keeps a sensor's number; rules conclude what it observes and its quantity, through a calibration the agent believes.
* [a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md) - A weather service is a sensor reading a series; sensing writes a graph per stretch; HTTP by its Thing Description; the location stays secret.
* [a-landing-is-a-band-and-a-world-holds-over-a-period](/decisions/a-landing-is-a-band-and-a-world-holds-over-a-period.md) - An action's landing is a band, least and most; a possible world holds over its path's summed period; the executor gives up past the latest.
* [a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md) - A drift answers a rate and rates add; the sum is accumulated between happenings, a crossing placed exactly, a range of rates a corridor.
* [a-drift-toward-the-surroundings-is-one-link-and-no-physics](/decisions/a-drift-toward-the-surroundings-is-one-link-and-no-physics.md) - A sample exchanges heat with what surrounds it: one link, a stated rate, the sign of the gap, no physics; the drift says when it crosses.
* [a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md) - A scope joins predicates on keys read per filling off the public graphs; the greenhouse's pump and heater are two scopes.
* [one-function-mints-every-want](/decisions/one-function-mints-every-want.md) - A desire is one; its met-test's violations are the instances in trouble, clustered by scope into wants; packages write instances and predictions, never wants.

# The market

The auction as a replaceable part: who convenes, who bids, how a round clears and what a claim is worth.

* [auction-and-clearing-are-the-markets](/decisions/auction-and-clearing-are-the-markets.md) - `auction.py`, `clearing.py` and the market's types leave the kernel for the package; a claim embodies the kernel's commitment, which is what a valve fulfils.
* [settlement-speaks-rea](/decisions/settlement-speaks-rea.md) - Settlement is ordinary economic exchange, so REA's words are borrowed: a claim is a commitment, actuation the event.

# Vocabulary — one word, one owner

Which package owns a word, what happens when one moves, and how a deployed volume follows.

* [every-term-in-its-own-house](/decisions/every-term-in-its-own-house.md) - Five packages took namespaces of their own. A term is named seven ways, and a rename sees one of them.
* [a-stand-in-is-not-a-device](/decisions/a-stand-in-is-not-a-device.md) - Observing is not something only a built thing can do, so a role asks for the role; substrate and existence are two other questions.
* [the-dictionary-names-its-terms](/decisions/the-dictionary-names-its-terms.md) - A domain page binds its word to the declared term in frontmatter, and a test holds the join; external vocabularies are vendored to check against.

# Knowledge, graphs and provenance

What the store holds, which engine reads it, and how a fact says who put it there.

* [who-put-the-fact-there](/decisions/who-put-the-fact-there.md) - Public knowledge is graphs split by who put the fact there. A SELECT that names one reads only part, silently.
* [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md) - Entailments are materialised into the store at genesis, so shapes and the runtime cannot disagree about the vocabulary.
* [metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md) - SUPERSEDED — every package counted its own through the choir, which went with 0.1.0; metrics are package selects now.
* [the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md) - Reaching the society is a capability the fact of a bus grants; the transport's module holds the connection, the loop and the watchdog.

# Packages and layout

A directory is a package. What that buys, and what the tree is not allowed to imply.

* [a-family-is-closed-and-that-is-a-choice](/decisions/a-family-is-closed-and-that-is-a-choice.md) - Only the package declaring a family may add members, so an external repo brings new abilities and not alternative implementations.
* [capability-packages](/decisions/capability-packages.md) - A package is one directory holding its own ontology, shapes, rules, code and namespace — found by looking, never listed.
* [one-tree-and-one-mechanic](/decisions/one-tree-and-one-mechanic.md) - One tree, `packages/<family>/<name>/`, with the family read off the path and declared nowhere.
* [every-package-is-a-project](/decisions/every-package-is-a-project.md) - Each package is its own distribution with its own dependencies, held to what it imports in both directions.
* [a-layer-is-a-package-and-need-loads-it](/decisions/a-layer-is-a-package-and-need-loads-it.md) - A layer is a family in the one tree, pulled by hard dependency from what is granted; a soft need injects and never loads.
* [a-term-nobody-reads-is-annotation](/decisions/a-term-nobody-reads-is-annotation.md) - The confirmation route is retired; the cognitive rows survive the same audit, because assembly reads them.
* [repository-layout](/decisions/repository-layout.md) - One convention across the Python trees, one distribution, and a packaging boundary replaced by a test and an import contract.

# Collections, services and what each is named for

A repository holds data and a service holds logic. Which of the model's parts is which, what
each is called, and what a name has to answer to.

* [a-read-is-a-function-over-a-store](/decisions/a-read-is-a-function-over-a-store.md) - The repository convention had two instances and both are functions now; a class earns its keep by owning a store.
* [a-graph-class-is-named-for-what-it-holds](/decisions/a-graph-class-is-named-for-what-it-holds.md) - A graph class is named for the rows it holds — desire graphs, want graphs, the asserted one both; the pick record's name says picks.
* [a-kind-is-a-type-not-a-binding](/decisions/a-kind-is-a-type-not-a-binding.md) - `orexis:Always` told six readers which KIND a node was; the type does that now, and `Want` is no longer a subclass.
* [a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md) - The type is the quantifier and the graph's period is the interval; `orexis:bindsWhen` states a third time what they already say.
* [a-situated-instance-is-kept-only-when-it-is-testimony](/decisions/a-situated-instance-is-kept-only-when-it-is-testimony.md) - A long-lived object and situational data about it, three times; only testimony is stored.
* [an-update-takes-no-dataset](/decisions/an-update-takes-no-dataset.md) - A query is handed its graphs per call, an update is not: the derivation may become updates over materialised views; the search chooses, and stays Python.
* [judge-desires-then-derive-wants](/decisions/judge-desires-then-derive-wants.md) - One function over the store, held to a snapshot: it judges every desire and mints the wants, with nothing written between them.

# Hardware — boards, parts and wiring

A part is described once and fitted many times; a wire is a fact the world states.

* [pins-and-wires](/decisions/pins-and-wires.md) - A pin is metal, a role is abstract, and the wire is what people get wrong — which makes a rail fault refusable.

# Sensing and readings

From bytes on a topic to a quantity an agent believes — and who holds the clock.

* [sensing-owns-the-reading-pipeline](/decisions/sensing-owns-the-reading-pipeline.md) - Codec, pointer, scaling, the sensed writer, observations and `readings.rq` move to sensing; what is known is a choir hook.
* [the-region-want-is-sensings-want](/decisions/the-region-want-is-sensings-want.md) - Sensing derives the region want and answers what a reading looks like; the kernel derives no want and keys nothing by property.
* [one-agent-many-sensors](/decisions/one-agent-many-sensors.md) - Three of four combinations work, measured rather than assumed. Both failures come from a second kind of sensor on one subject.

# Firmware, alarms and stand-ins

What runs on the board, what it promises while asleep, and what pretends to be one.

* [the-sentinel-alarms-on-movement](/decisions/the-sentinel-alarms-on-movement.md) - The heartbeat says where the value is and the ULP says that it moved; the operating range sizes the trigger rather than being watched.

# Worlds, genesis and operations

Authoring a world, ratifying it, and what an amendment may do to a running agent.

* [genesis](/decisions/genesis.md) - Sovereign narrates, LLM drafts, sovereign ratifies, infra writes. Each output is a whole world; agents are born from it.
* [world-graph](/decisions/world-graph.md) - No config file: the world graph holds only topology; desire, limits, cadence and prices are each agent's private beliefs.
* [two-worlds-were-one](/decisions/two-worlds-were-one.md) - Two worlds differed by 45 lines with identical beliefs, so the one that needs no hardware stayed.
* [an-amendment-endows-what-it-grants](/decisions/an-amendment-endows-what-it-grants.md) - Never-held terms arrive with their structures; held terms stay the agent's whatever their value.
* [a-dead-session-is-resigned-not-endured](/decisions/a-dead-session-is-resigned-not-endured.md) - An agent cut off from its bus sends itself SIGTERM; the container's restart policy is the recovery.
* [a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md) - Every reader, the boot included, loads only the kinds it reads; packages, brokers, series and deployment follow.

# Gates and guards

Each of these is a gate that went green while something was broken. The record says what it could not see.

* [a-test-that-asserted-nothing](/decisions/a-test-that-asserted-nothing.md) - Four guards went green while checking nothing. A root conftest fails the run if a test executed no assert.

# Direction

* [roadmap](/decisions/roadmap.md) - Where 0.2.0 stands, the open issue chains in order, and the parked extensions with the seam each needs.
