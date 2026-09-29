---
type: Decision
title: A package starts itself, and the runtime is a lifecycle container
status: accepted
timestamp: 2026-09-29T12:00:00Z
description: >-
  The sovereign's ruling of 2026-09-29, on reading #853. The runtime stops deciding what a
  package does: every package the agent loads beyond the mind that has a start module is handed
  the runtime and says what it does, by what the runtime offers - submit a job, hear a
  kind a job writes, every so many seconds, and at first a gauge. A transport listens or polls, sensing
  asks after what has fallen due, prediction answers an observation. Every job runs on one
  thread, one at a time, and packages meet at the store, never by calling each other. The mind
  starts itself next. Refused - the runtime orchestrating the order, packages running
  concurrently, packages calling each other, and a new word for the container.
---

# The claim

**The runtime is a lifecycle container.** It boots, finds the packages whose premise holds,
creates a [part](/domain/kernel/part.md) of each, links them, starts them, runs until the process is
stopped, and stops each, the last first. What a package does once started is the package's to say:
`agent/<package>/create.py` exports `create(runtime)`, and the part it answers links to the others
where it hears them, starts, and stops where there is anything to stop; the runtime imports it by
the package's name and knows no word of what it does.

**A package is offered four things, and nothing else.**

- `submit(job)` queues a callable, answering the graphs it wrote, from any thread: a
  transport's listener hands its message on this way.
- `on(kind, handler)` runs `handler(graph)` for every graph of that kind a job reports writing:
  prediction hears `orexis:StateGraph`, and revision, until belief starts itself, every graph.
  The belief base is the interface between the layers
  ([layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)),
  and a package learns of another's work by what was written, never by who wrote it.
- `every(seconds, job)` runs a job at the first pass and every so many seconds of the one
  timeline after. The runtime does the waiting and the package says what it waits for, which is
  the principle "the layer that waits does the waiting" kept rather than broken: MQTT asks
  after its sensors' missing readings every minute, HTTP polls each sensor at its
  `ssn-system:Frequency`, sensing asks after silence every minute.
- ~~`gauge(read)` reports what a package samples at a metrics window's end~~ — retired by
  [metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md):
  what a store holds is a level on an event its owner says.

**Every job runs on one thread, one at a time.** A package owns when and what; the runtime owns
where. `drain(now)` runs what is due, then every job queued and every job its writes set off,
until none is left; a pass is that drain, then the planner's pass and the executor's walk, as
before. No two jobs write at once, so a prediction never reads between an observation forgotten
and its replacement written, and a test drains by hand rather than timing threads.

**A transport starts where the runtime is told to connect.** `main` is; a test hands a member it
brought up, and the runtime links and starts it the same way. A member's `start` binds its thread's
messages to `submit`, opens what it listens on, schedules what it does of its own accord and is
attached; a step's command goes out through it because execution's part, linked to it, hands it on; several are held behind `Transports`.

# What was refused

- **The runtime orchestrating the order.** `Runtime.sense` drained the transport, revised,
  predicted and asked what had fallen due, in that order, and `_imported` named each package's
  function; the runtime was the one place every package's behaviour was written, which is what
  [the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md) refused for the
  transport and #843 showed the cost of - silence asked after only when some other message came.
- **Packages running concurrently.** Truer to each living its own life, and every read-then-write
  would need a lock or a transaction; the queue buys that for nothing, and a package's thread
  - a listener, a fetch - only ever submits.
- **Packages calling each other.** Sensing calling prediction after writing is simpler to follow,
  and is the coupling this takes out of the runtime put back into the packages.
- **A word of its own for the container.** The sovereign said "body"; the bundle calls the
  container the runtime, and a second word for it would be the synonym the dictionary refuses.

# What it supersedes

- The principle "a pass senses, revises, plans and walks, on one thread" becomes: a pass drains
  the packages' jobs, then plans and walks, on one thread.
- [a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md),
  in part: a forecast is no longer asked for by `missed`; the HTTP member polls it at the
  sensor's frequency.
- #853's pacing: MQTT no longer paces calls it is handed; it asks after missing readings on its
  own minute.

# Seams left open

- ~~The mind still runs its pass in the runtime~~ and ~~who keeps the agent alive is the
  runtime's reading~~: both closed by
  [planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md).
  Belief, planning and execution start themselves; a listening transport and a planner holding a
  desire hold the agent, and Hanoi's lets go; a package's signals are its own object's, connected when
  the parts are linked, and a graph written by kind is the runtime's one.
- **A transport member reads sensing's `cadence_of`** to poll at a sensor's frequency, a second
  downward import beside the callback.
