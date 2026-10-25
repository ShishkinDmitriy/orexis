---
type: Decision
title: A replay is the history drawn, and the package that decides a thing draws it
status: accepted
timestamp: 2026-10-25T20:00:00Z
description: >-
  The sovereign's ruling of 2026-10-25, after two couriers meeting head on became hard to follow from logs. The
  flight recorder is the history part, planning and coordination now say what they decided as points, and
  orexis-replay draws every agent's history - a core naming no package's word, a scene each domain draws of its world
  and a layer each package draws of what it decided, Preact components in TSX beside their code, typed by the core's
  contract and bundled by esbuild. Refused - a catalogue of view kinds a domain picks from, untyped htm with no build,
  recording the belief base, and a replay reading a volume. Amends rule 2 - a domain ships how it is drawn, which no
  agent runs.
---

# What was true

The lane's two couriers asked, answered, drew lots, laid what they yielded to and planned round it, and what any of
that looked like was read from two interleaved logs. The history held every observation and every step taken and
answered ([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)), so a
van's fix was there and its plan, its peer's word and its conflicts were not. The sovereign asked for a flight
recorder, *tightly coupled with events and history*, and of what draws it: *a courier world shows a grid with vans, a
terrace draws plants and weather — the package itself defines exactly how it is rendered.*

# The claim

**The recorder is the history, and what a replay needs that the history lacks is a point the agent does not yet
write.** That is reflection's rule ([reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md))
applied to a run instead of a season. Planning's `PlanPublished` carries its steps and answers a point per step;
coordination's part says the holdings each question carried, the holdings it laid of each peer — said, or foreseen
of a silent one — and every conflict, each set said whole and again only where it changed. A point names no agent,
since a bucket is one agent's; a process walking several installs a sink per agent, and the history part asks for
its own.

**`orexis-replay` draws it, and never opens a volume.** It reads every agent's history bucket as `orexis-explain`
does, or a recording a world's test made of a walk, and writes one page.

**The package that decides a thing draws it** ([replay](/domain/onboarding/replay.md)). The page's core names no
package's word: the instants, the agents shown, the log. Everything drawn is a `replay.tsx` beside the code or the
documents it draws: a domain's **scene**, the ground its world stands on — the courier's road, a grid with its vans
fixed and its contacts seen — and a package's **layer**, what it decided drawn on whatever scene there is —
coordination's holdings and conflicts, planning's path, execution's step in flight. A layer asks the scene one
thing, where the values a point carries put it, so coordination draws a holding on the courier's road and would
draw one on a terrace without a word of either. Each is a module of Preact components in TSX, exporting what the
core's contract (`onboarding/replay/core/index.ts`) says, which TypeScript holds it to; esbuild bundles the core and
every drawing a world uses into one page that opens offline. The toolchain is `npm ci` at the root, the operator's and
the tests', and no agent's.

**A replay is for many agents.** Every agent's layers are drawn in its own colour on one scene, so a world of dozens is
one road with every van on it; the agents shown are picked, and *side by side* gives each a pane of its own to compare
what two believed. A run is thinned before it is written — a sensor's reading the same as the one before on its
series is left out — and a point names its series by index; a drawing reads an agent's points of one measurement up
to the instant shown (`of`), so a step of the scrubber costs what the drawn measurements hold and not the whole run.

**Rule 2 is amended: a domain is documents and no code an AGENT runs.** Its `replay.js` is how it is drawn, which no
agent loads and which the operator's tool reads beside the domain's documents; a world may draw itself the same way.

# What was refused

- **A catalogue of view kinds the core renders and a domain picks from** — this record's first version, built and
  refused by the sovereign the same day: `onboarding:Grid` with two axes a domain's document filled in. A domain
  could only ever be drawn as something the core already had, so a terrace's plants and weather waited on a renderer
  in onboarding, and onboarding's vocabulary grew a word for every picture any domain wanted.
- **Recording the belief base** — every graph the runtime writes, which the `written` signal already says, replayed
  into a store per instant. It would show everything, which is the trouble: it is the volume by another door, the one
  thing reflection's record refuses to read, and no package would say what of it is history.
- **The replay reading a volume**, for a run whose history is thin. A figure a replay lacks is a point to add to the
  package that decides it, as this record adds planning's and coordination's.
- **Preact with `htm` and no build** — this record's second version, built and refused the same day: tagged template
  strings standing in for JSX, each drawing a function registering itself on a global, nothing typing what a scene
  and a layer are handed, and a pane per agent side by side. Hard to extend and blind to a mistake until a page drew
  it; and a pane per agent was thirty unreadable grids for thirty agents, every point of every agent written whole
  into the page at sixteen megabytes. A build step is the price of JSX and types, and the operator's tool can pay it.

# Seams left open

- **The courier's road is the one scene.** A terrace's plants and weather, a greenhouse's beds, are a `replay.js` in
  their domains when someone wants to watch them.
- **What each agent believed, not the world's truth.** The simulator knows where every van and hedge truly is and
  writes no history; a third source drawn beside the agents' would show where a belief went wrong. The trigger is a
  run where two panes disagree and neither is the world.
- **A set said again only where it changed** is the part's memory and not the store's, so an agent restarted says
  each set once more on its first pass; harmless, since a set replaces the one before.
- **The tests render under Node and need `npm ci`**, which the agent job runs; a world's test holding a drawing needs
  both too.
- **One page, whole.** A season of dozens of agents is read and written at once; a small server reading the buckets
  as the scrubber moves is the next step, when a page thinned and windowed is still too large.
