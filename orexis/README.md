# orexis: the kernel

What every package meets at, and nothing a package owns: the store and its catalogue, the clock, the boot that
makes one agent's store from its world's documents, and **the events**, the one thing packages share.

- **Loaded for:** every agent. It is no package and has no task.
- **Words:** `ontology.ttl` (`orexis:`): `orexis:Event`, `orexis:Incident`, `orexis:LogRecord`, `orexis:Role`,
  `orexis:plays`, the graph kinds packages meet at.
- **Dictionary:** `knowledge/domain/kernel/`, first `package.md`, `event.md`, `activity.md`, `policy.md`.

## What it gives a package

A package is one task registered by the linker (`task::Package`) and handed four things (`task::Handed`):
the store, the clock, the events, and what reaches outside. It registers the documents it brings with it
(`orexis::documents!("ontology.ttl", "rules.ttl")`), compiled into the binary; the boot puts them in the store where
a role of the agent loads the package, and reads no directory of crates.

| A package | by |
|---|---|
| subscribes to an event class or a graph kind | `Events::hears()`, `Hears::event`, `Hears::graph` |
| waits for an event, a graph written, an arrival or the clock | `Hears::next`, `Arrived::wait`, `Handed::sleep_until` |
| starts and ends an activity | `Turn::begin`, `Turn::end` |
| says an event | `Turn::emit` |
| says which graphs its turn wrote | `Turn::done` |
| holds the agent running, or lets it go | `Turn::hold`, `Turn::release` |

## Triggering events and activities

None of its own. It declares the top classes: an event is an instant, an activity is a span with a start and an
end, and a package's policy starts an activity for an event beneath that activity's trigger class.
