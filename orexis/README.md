# orexis: the kernel

What every package meets at, and nothing a package owns: the store and its catalogue, the clock, the boot that
makes one agent's store from its world's documents, and **the events**, the one thing packages share.

- **Loaded for:** every agent. It is no package and has no task.
- **Words:** `ontology.ttl` (`orexis:`): `orexis:Event`, `orexis:Incident`, `orexis:Logged`, `orexis:Role`,
  `orexis:plays`, the graph kinds packages meet at.
- **Dictionary:** `knowledge/domain/kernel/`, first `package.md`, `event.md`, `activity.md`, `policy.md`.

## What it gives a package

A package is one task registered by the linker (`task::Package`) and handed four things (`task::Handed`):
the store, the clock, the events, and what reaches outside. It brings its documents itself as it joins the agent,
which it decides itself, each a file of its crate compiled into the binary (`orexis::documents!("ontology.ttl",
"rules.ttl")`), and the boot reads no directory of crates.

| A package | by |
|---|---|
| decides whether it runs, first thing in its start | `Handed::plays` (its role), or a reason of its own |
| joins, bringing its documents, and waits for what its roles depend on | `Handed::joins` |
| says it booted, its core made, and waits until every package has; runs only where the agent does | `Handed::booted` |
| is checked: says what it found as its core is made | `Handed::checking` |
| has work left once every running package has ended | `Handed::stopping` |
| subscribes to an event class or a graph kind | `Events::hears()`, `Hears::event`, `Hears::graph` |
| waits for an event, a graph written, an arrival or the clock | `Hears::next`, `Arrived::wait`, `Handed::sleep_until` |
| starts and ends an activity | `Turn::begin`, `Turn::end` |
| says an event | `Turn::emit` |
| says which graphs its turn wrote | `Turn::done` |
| holds the agent running, or lets it go | `Turn::hold`, `Turn::release` |

## Triggering events and activities

It begins and ends the activities of the agent's lifecycle, `orexis:AgentBooting`, `orexis:AgentRunning` and
`orexis:AgentStopping`, and each package's inside them, `orexis:PackageBooting`, `orexis:PackageRunning` and
`orexis:PackageStopping`; inside a booting a package says `orexis:PackageJoined`. It declares the top classes: an event is an instant, an activity is a span with a start and an
end, and a package's policy starts an activity for an event beneath that activity's trigger class.
