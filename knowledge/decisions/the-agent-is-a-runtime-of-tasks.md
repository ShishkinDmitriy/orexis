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
  production, and a lock around the store. Amended 2026-11-12 - a package starts itself on the runtime and its task's loop
  is its own; the kernel keeps no order between two packages, and a test's pass tells them the instant in turn. Refused then - the
  runtime's loop over a trait of callbacks, a seat keeping the queue's order for the tests, and registration found by
  the linker.
---

# What was true (on main at b8805ccf)

The runtime (`orexis/src/runtime.rs`) runs every part on one thread. A pass drains one queue of jobs in the order they
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

# Amended 2026-11-12: the loop is the package's, and the runtime knows no package

As first built (#1142) the runtime kept the loop: one generic task per part, written in the kernel, calling a `Part`
trait the package implemented - `start`, `run(job)`, `heard`, `heard_event`, `submitted`, `stop`. A package was
callbacks, and its policy was polled; that is the one ordered queue this record refused, cut into a queue per part.

**The runtime is a Tokio runtime and a watch, and a package starts itself on it.** Its `create` module's `start`
takes a wait from the runtime, says on it what ends it - an event's class, a kind of graph written, a timer - takes
the runtime's watch as where it says its events, and spawns its task. The task's loop is in the package, awaiting
`Wait::next`, which answers what woke it and the `Pass` it is handled in. The kernel has no trait a package
implements and no type a package registers by; whoever assembles an agent builds the runtime and calls each
package's `start`. What the first paragraph of *What was decided* says goes stays in part: `Pass` is what a part
woken is handed - the instant, the agent's life, `wake_at` - and `drain` is how a test says the instant; the job
queue is gone, a part that queues work for itself keeping its own.

**The kernel keeps no order between two packages; a test's pass still tells them the instant in turn.** Run free a
package is woken by what triggers it and decides once nothing more waits for it. By passes the runtime says the
instant: a pass tells each wait in turn, in the order the packages started, that it is now, waits until nothing is
busy, and everything said in the pass is handled at that instant, so a test's clock is read once a pass. A policy
decides when it is told the instant, and what it hears after that it decides on at the next pass; what a package
queued for itself in a pass it does at the pass's end, once. Those two rules are what is left of *The order the
tests prove*, as two branches of a wait and no longer a machine of steps, and the digests stood. Both were tried
without and are kept because the worlds lean on them. A plan published is walked in the pass that published it only
because planning started before execution; and a walk done after each thing heard, not once a pass, read a test's
clock twice more a pass and the allotment's second round fell elsewhere. They go when a test sets the clock
instead of running passes.

**The pass had also paced a retry, and planning now does.** With a policy deciding after every message, a plan that
fails as it is taken was planned again at once, in the present it failed in, for ever: run free, the greenhouse's
dry bed with a silent probe published seventy plans in eight seconds, where a pass had made it one a pass without
anyone saying so (#1145). Planning's policy now holds back: a want whose plan, published since news was last heard,
has ended with the want still standing is not planned again until news is - a revision that changed a state or
revised a belief that came to the agent, never its own record of what it did, a committed step among them
(`orexis:Recorded`). Refused for it: a rule on what was heard alone, "what execution says of a plan is no trigger
while no belief was revised", which also kept planning from laying the grounds a committed dose changes; and
planning naming execution's events to tell a failure, a lower package speaking a higher one's word. And a run
halted while something is still busy now ends, where it waited for a rest that never came. One rule of the
queue's is kept for good, being about one package and not two: what a package says while it handles what woke it
is heard once it has said what it wrote, its graphs before its events, so a hearer never starts on a sayer's
half-written work.

**A search runs in place** (`runtime::long`, Tokio's `block_in_place`): its worker hands its other tasks on, so the
sessions and the other policies keep theirs. `spawn_blocking`, which this record named, needs the search to own what
it searches; it waits for the scopes to run free, the part of #1119 step 8 not yet built.

Refused:

- **The runtime's loop over a trait of callbacks** - what was built first. It made the kernel the place every
  package's shape was decided, and a part could wait for nothing the trait had no method for.
- **A seat that kept the queue's order for the tests** - what was built second, the same day: a package registered a
  boxed closure the runtime called in order, and its task waited on a seat whose steps replayed, by passes, the
  order one queue ran them in. It cost the kernel a second way of running that no deployed agent ever ran; the
  sovereign refused it, since the packages are independent and the one thing they share is where they say their
  events.
- **Registration found by the linker** (a distributed slice each crate submits to). A part is made from what only
  the assembler holds - a member a test hands, a budget, the model - so something must still name each package once;
  that is the binary's features, as before.
- **A tag per subscription replaced by matching on an event's class.** A part hears a class and every class beneath
  it, so the class said is not the class asked for; the tag is how the part knows which of its triggers woke it.

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
