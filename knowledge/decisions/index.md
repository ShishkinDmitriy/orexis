# Decisions

Architecture decisions, ADR-style: context, the choice, why, and — where it matters —
the *seam* deliberately left open for a later stage. Read these when you're about to
change something, to check you're not welding shut a planned extension.

# Core architecture

* [trust-boundary](/decisions/trust-boundary.md) - Agents cite but never author facts, mint currency, or actuate. Three privileged powers stay in trusted infrastructure.
* [thin-trusted-infra](/decisions/thin-trusted-infra.md) - Relax the powers toward public functions + signed artifacts + bounded devices; the one irreducible trusted thing is the currency ledger (double-spend).
* [llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) - Thin BDI: the LLM drives deliberation; the formal layer becomes load-bearing, not optional.
* [deterministic-bid](/decisions/deterministic-bid.md) - The bid number is code; the LLM only produces the justification. Rhetoric can't move the number.
* [english-vs-formal](/decisions/english-vs-formal.md) - English for what's contested, formal (RDF/SHACL) for what's trusted.
* [agent-centric-epistemics](/decisions/agent-centric-epistemics.md) - Judgment, private data, and perception belong to the agent; infra is thin honest mechanism; author by stake; disclose need-to-know; observe via sovereign.

# Identity & authorization

* [authn-authz-capabilities](/decisions/authn-authz-capabilities.md) - Cert = who you are (durable); signed capability grant / JWT = what you may do now (ephemeral). Revoke only on provable violation.
* [one-agent-many-sensors](/decisions/one-agent-many-sensors.md) - Three of the four combinations work, measured rather than assumed. The two that do not are both triggered by giving one subject a second KIND of sensor: an observation keyed by subject alone, and sensors that the derivation splits but the runtime does not.
* [wokwi-drafts-it-the-world-ratifies-it](/decisions/wokwi-drafts-it-the-world-ratifies-it.md) - Importing a diagram DRAFTS a stand and never becomes its source: the mapping is invertible, but Wokwi recovers the shape of a wiring and none of its meaning. Bidirectional sync was refused rather than deferred, because a world synced from a drawing has nothing left to refuse.
* [pins-and-wires](/decisions/pins-and-wires.md) - The core vocabulary splits into a stand plus a package per protocol and per part; a pin assignment becomes a pin, a role and a wire. A pin is metal, a role is abstract, and the wire is what people get wrong — which is what finally made the rail-voltage fault refusable.
* [repository-layout](/decisions/repository-layout.md) - One convention across six Python trees, one distribution instead of two, and a packaging boundary replaced by a test and an import contract — both verified by breaking them. Why capabilities live inside the agent and the vocabulary does not.
* [series-and-bus-isolation](/decisions/series-and-bus-isolation.md) - A bucket and a scoped token per agent, and per-principal broker credentials whose topics are derived from the same wiring that derives capability. Closes the two holes where-the-belief-base-lives left open.

# Economy

* [single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md) - One wallet for water and compute; thinking costs, so bounded rationality is priced in.
* [strategic-supplier](/decisions/strategic-supplier.md) - The supplier is a genuine seller with costs and a reserve price (Design B), not a stake-free utility.
* [the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md) - A round is triggered by a band and sized by a fixed host belief, so its size has nothing to do with what anyone needs — the host is deliberately blind to quantity until bids are in. Measured: half the lot can be wanted by agents none of whom can convene a round.
* [clearing-as-validator](/decisions/clearing-as-validator.md) - The scarce side runs the auction; clearing is a thin stake-free notary that checks integrity and co-signs the trade before settlement.

# Belief base

* [two-store-beliefs](/decisions/two-store-beliefs.md) - InfluxDB owns the series; Fuseki owns citable current-state. Joined by plant URI, never federated.
* [world-graph](/decisions/world-graph.md) - No config file: the world graph holds only topology (public, versioned, stated once); desire, limits, cadence and prices are each agent's private beliefs. Agent/Sensor/Actuator become first-class.
* [capability-modules](/decisions/capability-modules.md) - Code reads T-Box terms, never instances. A capability is an ontology module + shapes + derivation rules + code; capabilities are derived from hardware at genesis, and each agent is its own process knowing only its id. (Superseded on packaging by capability-packages.)
* [who-holds-the-clock](/decisions/who-holds-the-clock.md) - Perception is three capabilities on one axis: Polling (the agent asks each time — declared, reserved, no hardware for it), Subscribing (the agent states an interval the device keeps — what the ESP32 does), Listening (the device announces). What was called Polling was Subscribing all along.
* [a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md) - A belief is a point chosen inside a range, not a constant: what genesis wrote is the first pick and the constraints (world, sensor, self) are the bound. Which terms may be re-picked is one triple in the owning package's ontology; a rule is SPARQL, not code; legitimacy is the boot check re-run. A summary is a belief and a reading is a measurement, so history stays in Influx.
* [capability-packages](/decisions/capability-packages.md) - A capability is one directory holding its own ontology, shapes, derivation rules, beliefs and code — found by looking, never listed. Capabilities reach each other through T-Box terms, never Python imports, so adding one is adding a directory and removing one is deleting it.
* [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md) - Shapes inferred and the runtime did not, so a world could validate against a relationship the code would never observe — and six queries walked subclass paths by hand for twenty-five declared axioms. The entailments are materialised into the store at genesis; validation runs with inference off against that same graph, and a test fails if the two ever diverge.

# Genesis

* [genesis](/decisions/genesis.md) - Sovereign narrates → LLM drafts → sovereign ratifies → infra writes structure + charters. Each output is a whole world (world/ holds several, one loaded at a time), and agents are born from it — the deployment is generated from the world, one container per agent. Amendable and versioned; structure mutable, history immutable.

# Seams (open on purpose)

* [standalone-clearing](/decisions/standalone-clearing.md) - The scarce side hosts the auction (host rotates with topology); the clearing validator stays invariant.
* [bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md) - Bids reflect current unmet need, so multi-source decomposition stays possible.
* [where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md) - A shared triplestore couples worlds that are meant to be independent: adding the 21st restarts the other 20. The world becomes TTL files an agent loads at start, beliefs live in a persistent store inside each agent, no shared store survives, and validation moves into the agent.
* [belief-base-isolation](/decisions/belief-base-isolation.md) - SUPERSEDED in mechanism by where-the-belief-base-lives, though its reasoning about why the graph is the write boundary still holds. Privacy was enforced by the store: per-graph ACLs behind per-agent credentials. It is now structural — there is no shared store to be let into.
* [roadmap](/decisions/roadmap.md) - What v1 is, and the v2/v3 extensions each seam unlocks.
