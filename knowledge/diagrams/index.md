# Diagrams

One picture of Agent 0.2.0, and Agent 0.1.0's: one per service of the retired kernel, the mind as
a whole, and the cone. The [0.1.0 records](/decisions/0.1.0/index.md) embed theirs. Each is
PlantUML source with a rendered SVG beside it.

* [agent-structure](./agent-structure.puml) - Agent 0.2.0: each package with its services and the graph kinds it declares, who writes each — held to the ontologies by a test.
* [agent-structure-0.1.0](./agent-structure-0.1.0.puml) - Six modalities, one repository each, and the services beside them — 0.1.0's target, with its delta marked.
* [service-planner](./service-planner.puml) - The search: what it reads to simulate, and the two possible-modality graphs it writes.
* [service-deliberator](./service-deliberator.puml) - The whether, and the trace it clears before each pass.
* [service-executor](./service-executor.puml) - Plan, commit, take — a service that writes no graph because it only orchestrates.
* [service-keeper](./service-keeper.puml) - The ledger's only writer, and the three jobs that share it.
* [service-ower](./service-ower.puml) - The debts this agent carries, durable across a restart.
* [collection-steps](./collection-steps.puml) - What could be done, derived per ask and stored nowhere; what the steps collection reads.
* [service-deducer](./service-deducer.puml) - What is pursued, and the one service living inside the repository it writes.
* [service-inference](./service-inference.puml) - The closure, and the only case where a graph's type does not distinguish it from its source.
* [service-reviser](./service-reviser.puml) - The seam: a service with no repository at all, because a mark is not a belief.
* [time-two-cones](./time-two-cones.svg) - One tree of possible worlds on a time axis, the two kinds of edge, and the ground a node stands on.

The runbooks' pictures, one per runbook that embeds it:

* [runbook-world-documents](./runbook-world-documents.puml) - A world's documents: read by every agent on each restart, each agent's own at birth, onboarding's alone.
* [runbook-change-costs](./runbook-change-costs.puml) - What a change to a running world costs: a restart, a build, a fresh belief volume, or onboarding.
* [runbook-observer-documents](./runbook-observer-documents.puml) - Which document states the subject, the sensor, the agent, the board, the topic and the observer role.
* [runbook-observer-reading](./runbook-observer-reading.puml) - One reading, from the board to a belief planning reads.
* [runbook-predictor-flows](./runbook-predictor-flows.puml) - The flows' rates summed from each ground, a ground at every crossing, and a want for a foreseen instant.
* [runbook-planner-loop](./runbook-planner-loop.puml) - From a desire read unmet to a command on a device, and the reading that shows it landed.
* [runbook-market-round](./runbook-market-round.puml) - A bidder calls, tenders, wins a claim and presents it; the host doses its plot.

# One class diagram per crate

Each is generated from its crate's `src/` by `tools/class-diagrams.py` and held to it by `tests/test_knowledge.py`, so none is edited by hand:

* [package-orexis](./package-orexis.puml) - The kernel: the store, the events, the clock and what a package is handed, by module.
* [package-orexis-actuation](./package-orexis-actuation.puml) - Actuation: a step's command turned into the settings a device is sent.
* [package-orexis-agent](./package-orexis-agent.puml) - The binary: one agent's process, booting the world and starting the packages its roles load.
* [package-orexis-belief](./package-orexis-belief.puml) - Belief: the deliberator, its rules and transitions, and what a revision writes.
* [package-orexis-coordination](./package-orexis-coordination.puml) - Coordination: the coordinator, the draw and what a conclusion holds.
* [package-orexis-execution](./package-orexis-execution.puml) - Execution: the executor and the events its walk says.
* [package-orexis-journal](./package-orexis-journal.puml) - The journal: what it keeps of every event and activity, and the recorder's role.
* [package-orexis-journal-otlp](./package-orexis-journal-otlp.puml) - The journal's tracer: what ships its activities over OTLP.
* [package-orexis-journal-oxigraph](./package-orexis-journal-oxigraph.puml) - The journal's archive: what takes its entries to disk.
* [package-orexis-llm](./package-orexis-llm.puml) - The model family: a model, how a role asks it, and the client.
* [package-orexis-metrics](./package-orexis-metrics.puml) - Metrics: the meter and the tallies it writes each window.
* [package-orexis-planning](./package-orexis-planning.puml) - Planning: the planner, the memo, the grounds and the events a pass says.
* [package-orexis-prediction](./package-orexis-prediction.puml) - Prediction: the predictor and the flows it integrates.
* [package-orexis-sensing](./package-orexis-sensing.puml) - Sensing: the observer, its attentions and the events a reading says.
* [package-orexis-sensing-influxdb](./package-orexis-sensing-influxdb.puml) - Sensing's housekeeper: what writes the readings to the series store.
* [package-orexis-speech](./package-orexis-speech.puml) - Speech: what is heard and said, and the extraction that makes a belief.
* [package-orexis-translation](./package-orexis-translation.puml) - Translation: the translator, its chats, styles and the model's tools.
* [package-orexis-transport](./package-orexis-transport.puml) - The transport family's contract: members, the inbox and the chat carrier.
* [package-orexis-transport-email](./package-orexis-transport-email.puml) - The email member: a mailbox over IMAP and SMTP.
* [package-orexis-transport-http](./package-orexis-transport-http.puml) - The HTTP member: a service reached over the web.
* [package-orexis-transport-mqtt](./package-orexis-transport-mqtt.puml) - The MQTT member: the agent's side of the bus.
* [package-orexis-transport-telegram](./package-orexis-transport-telegram.puml) - The Telegram member: an agent's own bot over the Bot API.

# A picture is an image, never a Mermaid block

GitHub's web view draws a Mermaid block and its mobile app shows the source as text, so the
runbooks' diagrams, written in Mermaid first, read as code on a phone. An SVG shows everywhere a
page does, and the stamp below holds it to its source.

# One picture is drawn rather than rendered

`time-two-cones.svg` has no `.puml` beside it and is not generated. Its geometry IS the idea —
two cones opening from one point on a time axis — and a graph-layout tool draws a graph, not a
picture: asked for this, PlantUML produced boxes in a column. So the SVG is the source, hand
authored, and there is nothing for it to drift from. The stamp below is for what a renderer
made; the gate reads `.puml` files, so it neither checks this one nor needs to.

# Rendering

```bash
./tools/class-diagrams.py         # every crate's class diagram, regenerated from its src/
./tools/render-diagrams.sh        # every source -> .svg, stamped with the source's hash
```

**A committed image is only safe because something notices when it stops matching.** The script
stamps each SVG with the sha256 of the `.puml` it came from, and
`tests/test_knowledge.py::test_a_committed_diagram_is_not_stale` compares that stamp to the
source. It needs no renderer — a gate that ran only where PlantUML is installed could not run on
a fresh clone. Rendering needs the tool; checking never does.

Edit a `.puml`, forget to re-render, and the suite says so by name.
