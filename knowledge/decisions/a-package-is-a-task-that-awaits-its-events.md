---
type: Decision
title: A package is a task that awaits its events and the clock, and nothing assembles it
status: accepted
timestamp: 2026-11-12T12:00:00Z
description: >-
  The sovereign's ruling of 2026-11-12, after the runtime of tasks was built twice. A package is one async function
  that makes its own core object, awaits the events beneath its triggers and the clock, and says what happened; it
  registers itself by the linker, and the binary names no package beyond linking its crate. What it is handed is
  plain - the store, the clock, the events, and what reaches outside - and there is no runtime object, no wait and no
  pass. A unit test holds a package's core and never an async function; a world's test boots the agent on Tokio's
  paused time, feeds its bus and awaits an event. Refused - the kernel's wait that multiplexed what woke a package,
  a clock of the agent's own kinds, parts lent to tests, and links made by an assembler.
---

# What was true

After [the-agent-is-a-runtime-of-tasks](/decisions/the-agent-is-a-runtime-of-tasks.md) and its amendment of the same
day, a package's task was its own loop, but every loop went through one kernel object: it awaited `Wait::next`, was
answered a `Woke` with a tag it had asked under, and was handed a `Pass`. Whoever assembled an agent built a
`Runtime`, made each part, linked three of them by hand - prediction's foresight to the planner, the taker to the
executor, the head check between planning and execution - and called each package's `start`. A test ran the same
tasks by passes: `drain(now)` told each wait the instant in the order the packages started, a policy decided when
told, and what a package queued for itself waited for the pass's end. The agent's clock was a trait with a paced,
a manual and several ticking kinds, each test bringing its own, and a read of a ticking clock was a second.

Three things leaned on the pass that nobody had written down, and each was found by taking it away: a plan was
walked in the pass that published it because planning started before execution; a plan that failed as it was taken
was planned again a pass later and not at once (#1145, since fixed in planning's policy); and the allotment's
second round fell where it did because the executor walked once a pass.

# What was decided

**A package is one async function.** It makes its core object - the Planner, the executor, the deliberator - holds
it, and loops: it awaits the events beneath its triggers, a kind of graph written, an arrival, or the clock, calls
its core, and says what happened. Nothing outside the task holds the core.

**It is handed four plain things and no object with behaviour of its own**: the store, the clock, the events - where
every package says what happened and subscribes to what it hears, the one thing packages share - and what reaches
outside, the connectors a deployment makes from its environment and a test hands in. A task hears everything it
asked for through one subscription, in the order it was said, each thing under a tag of its own: a subscription a
trigger was built first in the head and refused, since two channels keep no order between them and a test would
see either. Whether anything holds the agent is kept where the events are, and the binary ends the run on it.

**A package registers itself.** Its crate submits its name and its start to a registry the linker collects, and the
binary starts each one its roles load. The binary names no package but to link its crate, one line a feature,
since a crate nothing references is not linked. What an assembler linked by hand a package now finds for itself:
the planner asks the registry for foresight, and the executor asks the events whether anybody hears what it would
say - a command, a document told, a head asked - where it was told so.

**Waiting is Tokio's, and a test's clock is too.** A task waits by Tokio's sleep, for as long as the agent's clock
says an instant is ahead. A deployed agent reads the wall, at a pace where one is stated: the pace stays, as one
multiplication, since a world run fast in containers for a season's series ([reflect](/runbooks/reflect.md)) has
its simulator in another process, where Tokio's paused time cannot reach. A world's test reads an epoch and what
Tokio's clock has run since (`Elapsing`).

**A unit test never touches an async function, and a world's test awaits an event.** What a package decides is in
its core, sync, and held by its snapshot cases and its own tests; its task only waits and calls. A world's test
boots the agent as the binary does, on one thread with Tokio's time paused - which runs ahead whenever every task
is idle, so a day takes moments - feeds its bus, and awaits the event the scenario ends in, or lets a stretch of
time pass and holds that none was said. There is no pass, so no test counts one, and a replay is pinned to what
the tasks do.

**One happening is said once.** What one turn wrote of a kind is told as one thing, the graphs together: a message
of several readings is several percepts, which sensing says perceived together and belief revises together, saying
so once. Told a graph at a time, each reading was perceived and revised apart, and whoever heard the first
revision decided before the rest of the message was believed - the executor took a head its radar's reading, a
moment on, would have refused. A package is a function of what happened, and what happened is the whole of it.

**What a task says while it handles what woke it is heard when it next waits**, its graphs before its events, as
before: a hearer never starts on a sayer's half-written work.

# Refused

- **The kernel's wait.** One object answering what woke a package, by a tag, with the pass it is handled in. It
  made every package's loop the same loop, and it was where the two ways of running met; with one way of running
  it holds nothing a subscription and a sleep do not.
- **Clocks that tick at a read.** Each world's test brought one, so its time moved as its agents asked the hour,
  and a world's outcome depended on how many times they did. A clock a test sets by hand stays, for a core's own
  tests, which run no task.
- **A part lent to its test.** A test read the Planner between runs through a lock the task shared. What a test
  may hold of a running agent is what it said and what its store holds.
- **Links made by an assembler.** They were the last reason anything had to know two packages at once.
- **A subscription a trigger.** See above: order between what a task hears is kept by one stream.
- **Tasks declared in the binary's `main`**, as an embedded executor spawns them. The roles an agent plays are read
  at boot, so which tasks run is not known where `main` is written; a list there would be the assembler again.

# What it amends

- [the-agent-is-a-runtime-of-tasks](/decisions/the-agent-is-a-runtime-of-tasks.md): its tasks, its one writing
  package per graph and its search run in place stand. The order the tests prove, the wait and the pass go, and
  its refusal of registration found by the linker is lifted: a part is no longer made from what only an assembler
  holds.
- [a-package-starts-itself](/decisions/a-package-starts-itself.md): a package still has one way in, and the
  runtime it started on is gone.

# What it found

Run with no pass, on a clock that stands still while an agent computes, everything an agent does of one thing
happens at one instant, and several things the pass or a ticking clock had hidden came out: a search the budget cut
short was not continued while another plan was walking; a member woke itself for ever at the very instant a
reading fell due, sensing saying it had not lapsed yet and that its lapse was now; a wait until now was taken for a
wait; a hold meant for a plan that could not be taken also held back one whose landing was waited out. Each is
fixed where it was. What is not yet held on the new shape is an issue of its own, and its tests are set aside
until it is: the lane's two couriers (#1149), the unanswered dose's metrics (#1150), and two tests that read the
planner between passes (#1151). The allotment's market (#1148) was closed in its documents: a claim presented
declared no landing, so it failed a patience on and the grower bought again until its probe next read. The tower's puzzle (#1147) was the first
closed: a ground is named for its instant, two plannings at one instant lay it twice, and laid again it kept the
candidates its earlier facts had admitted, one of which a later search took.

# Seams left open

- **Scopes searched free of the task** (#1119 step 8) are still not built: planning's search runs in place.
- **A package reading across several queries during another's write** copies first, as before; nothing audits it.
