---
type: Decision
title: The agent is a runtime of tasks, each package's policy one of them, and a graph has one writing package
status: accepted
timestamp: 2026-11-11T20:00:00Z
description: >-
  The sovereign's ruling of 2026-11-11, on step 8 of #1119. The agent's body is a multi-threaded Tokio runtime, and
  the features it was built with say which tasks are registered: each package's policy is a task that awaits the events
  beneath its trigger and its own due instant, and starts its activities; a long computation leaves the workers for the
  blocking pool. One thread owning the store gives way to one writing package per graph, each update a transaction of its
  own, and a package that reads across several queries copies first; the order the tests prove is the single-threaded
  runtime's, ticking the parts in turn. Refused - one ordered queue on the mind, the same tasks on the mind's thread alone in
  production, and a lock around the store.
---

# What was true (on main at b8805ccf)

The runtime (`agent/src/runtime.rs`) runs every part on one thread. A pass drains one queue of jobs in the order they
were queued - each package's timers, the graphs written that a part hears by kind, the events said that a part hears
beneath its trigger - and then waits for an arrival or the soonest instant a part said it is due. Since #1119 steps 1
to 7 every part decides by its policy, no part links to another, and no part borrows anything. What already waits on
the outside is a Tokio task: each MQTT session's event loop, handing what arrives to the mind's inbox.

[packages-meet-by-events-policies-and-activities](/decisions/packages-meet-by-events-policies-and-activities.md)
refused "each handler a Tokio task" on three premises, and
[a-graph-changes-in-place-and-its-row-says-what-it-holds](/decisions/a-graph-changes-in-place-and-its-row-says-what-it-holds.md)
leaned on a fourth:

1. the parts held the store borrowed and their objects shared, so they were not `Send`;
2. a search does not yield, and would stall the sessions on its worker;
3. jobs run in the order they came is what lets a snapshot case and a digest hold the binary to one result;
4. one thread runs every part, so no two writers meet.

**The one thread was Python's.** The Python agent ran every part on one thread, and the port kept it: a ported
package was held to the Python agent's results, and a replay to what that agent sent, command for command, so the
binary ran its jobs in the order the Python signals fired. The Python agent was retired on 2026-11-09, and nothing is
held to its order any more; what one thread bought was that sameness, and Tokio offers the agent what Python's runtime
could not - workers, a blocking pool and paused time in a test.

The first premise is gone (step 7). The second is answered by where a computation runs, below. The third and fourth
are the cost this record pays, and says how.

# What was decided

**The agent's body is a Tokio runtime, and the features say what runs on it.** The binary builds a multi-threaded
runtime; each package its roles load, and this binary was built with, registers its tasks as it starts, and the
runtime knows no word of what they do. A package's policy is ONE task: it awaits the next event beneath its trigger,
or its own due instant (`sleep_until`, on the clock's pace), decides, and runs the activity it starts. What the pass
was - `Pass`, `drain`, `again`, the job queue - goes; `wake_at` is the task's own wait.

**An event is broadcast, and a task hears it by class.** What a part says is sent to every task whose trigger the
event's class is beneath, by the vocabulary's closure, as `hears` asks today; a graph written is said as an event of its
kinds. Each task receives in the order said by the one that said them; between two sayers no order is promised, which
is what point 3 gives up.

**A graph has one writing package, and an update is a transaction.** The single writer becomes one writer per graph:
the percepts are sensing's, the revisions belief's, the wants, the plans and the imaginarium planning's, the
intentions execution's, a statement speech's. What every package writes into - the catalogue - is written by single
SPARQL updates, each a transaction of the engine's, and a count the store keeps by reading and then writing is kept
by its one writer. A package that must read several queries against ONE state copies what it reads first, as a scope
prepares its imaginarium, since the engine has no snapshot a reader may hold.

**A long computation leaves the workers.** A task that computes for seconds - a scope's search - runs it on the
blocking pool (`spawn_blocking`), owning what it searches, so the sessions and the other policies keep their workers.

**The order the tests prove is the single-threaded runtime's.** A test runs the same tasks BY PASSES on Tokio's
current-thread runtime: the runtime ticks each part in turn and waits until nothing is busy before ticking the next,
no task arms a timer, since the test sets its clock, and two rules keep the order one queue gave - what a part
queues while the parts are ticked runs at the end of the pass, and the graphs a call wrote are told before the
events it said - so a replay gives the same digest every run, and the Python couriers' drives still. Production may
interleave two sayers otherwise; what it may not do is break a graph's one writer, which no interleaving can.

**The run ends when nobody holds the agent**, the holders a registry the tasks share, as `hold` and `release` are
today, and a signal raises the halt every task's wait hears.

# What was refused

- **One ordered queue on the mind** - today's runtime, kept for the packages, with Tokio for what waits outside and the
  blocking pool for the search. It keeps point 3 and 4 whole, and it keeps every policy waiting for the one before it in
  the queue; the sovereign's word is that the agent's body is the runtime and a package is the tasks it registers.
- **The same tasks on the mind's thread alone, in production** (a `LocalSet`). One writer and an order again, but the
  order is the scheduler's, which promises none, so it buys point 3 no better than the tests' runtime does and runs on
  one core of four.
- **A lock around the store.** It would make point 4 true by making every task wait for every other, which is the one
  queue again with a mutex for a queue.

# What it amends

- [packages-meet-by-events-policies-and-activities](/decisions/packages-meet-by-events-policies-and-activities.md), in
  part: its refusal of handlers as Tokio tasks. Its events, policies, triggers and activities stand; a policy is now a
  task.
- [the-agent-moves-to-rust-one-package-at-a-time](/decisions/the-agent-moves-to-rust-one-package-at-a-time.md), in part:
  "what waits is a task, and the mind is one thread" - every policy is a task, and no thread owns the store.
- [a-graph-changes-in-place-and-its-row-says-what-it-holds](/decisions/a-graph-changes-in-place-and-its-row-says-what-it-holds.md),
  in part: optimistic locking still has no work, now because a graph has one writing package, not one thread.

# Seams left open

- **Two sayers, no order.** A revision and a reading's arrival heard by planning in either order are both answered by
  planning's next activity, since a trigger heard while it plans is held for the one after. Where an order between two
  packages turns out to matter, it is an event one says after the other's, not a scheduler's promise.
- **A cross-package read during another's write** sees each update whole and the next one not yet; a package reading
  across several queries copies first. Which do is found as each policy moves, not audited ahead.
