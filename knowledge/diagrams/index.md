# Diagrams

One picture per service, plus the mind as a whole. Each is PlantUML source with a rendered SVG
beside it, and the pages embed the SVG.

* [agent-structure](./agent-structure.puml) - Six modalities, one repository each, and the services beside them — the target, with the delta from today marked.
* [service-planner](./service-planner.puml) - The search: what it reads to simulate, and the two possible-modality graphs it writes.
* [service-deliberator](./service-deliberator.puml) - The whether, and the trace it clears before each pass.
* [service-executor](./service-executor.puml) - Plan, commit, take — a service that writes no graph because it only orchestrates.
* [service-keeper](./service-keeper.puml) - The ledger's only writer, and the three jobs that share it.
* [service-ower](./service-ower.puml) - The debts this agent carries, durable across a restart.
* [service-afforder](./service-afforder.puml) - What could be done, derived per ask and stored nowhere.
* [service-deducer](./service-deducer.puml) - What is pursued, and the one service living inside the repository it writes.
* [service-inference](./service-inference.puml) - The closure, and the only case where a graph's type does not distinguish it from its source.
* [service-reviser](./service-reviser.puml) - The seam: a service with no repository at all, because a mark is not a belief.
* [time-two-cones](./time-two-cones.svg) - One tree of possible worlds on a time axis, and the two kinds of edge that run through it.

# One picture is drawn rather than rendered

`time-two-cones.svg` has no `.puml` beside it and is not generated. Its geometry IS the idea —
two cones opening from one point on a time axis — and a graph-layout tool draws a graph, not a
picture: asked for this, PlantUML produced boxes in a column. So the SVG is the source, hand
authored, and there is nothing for it to drift from. The stamp below is for what a renderer
made; the gate reads `.puml` files, so it neither checks this one nor needs to.

# Rendering

```bash
./tools/render-diagrams.sh        # every source -> .svg, stamped with the source's hash
```

**A committed image is only safe because something notices when it stops matching.** The script
stamps each SVG with the sha256 of the `.puml` it came from, and
`tests/test_knowledge.py::test_a_committed_diagram_is_not_stale` compares that stamp to the
source. It needs no renderer — a gate that ran only where PlantUML is installed could not run on
a fresh clone. Rendering needs the tool; checking never does.

Edit a `.puml`, forget to re-render, and the suite says so by name.
