---
type: Domain Concept
title: Package
description: >-
  A crate, `orexis-<package>/`, that owns a concern and the words for it — belief, sensing, prediction,
  planning, execution, speech, the MQTT transport — with its own namespace in its own
  `ontology.ttl`, importing only what lies beneath it. A domain is its counterpart outside the
  code - documents and no Python.
---

# What it is

The unit the agent is built of. Each package holds its Python, the ontology declaring its words
under its own prefix, its tests and its cases, and a layout test that holds it to three things: it
imports only packages beneath it, it speaks no word of a package above it, and an act-named module
exports that act alone.

| package | concern |
|---|---|
| `orexis-belief/` | revision: the rules a store holds, run over what was written |
| `orexis-sensing/` | an instrument's bytes become an observation |
| `orexis-prediction/` | when a reading will change range |
| `orexis-planning/` | desires and wants, the search, the plan |
| `orexis-execution/` | intentions, taking a step, the world's answer |
| `orexis-speech/` | a peer's document heard, the agent's own said |
| `orexis-transport-<member>/` | reaching the society, a crate per member: MQTT, HTTP, Telegram, email |

Nothing assembles them - each registers itself (`orexis/src/task.rs`) - and the kernel's `orexis:` vocabulary
(`orexis/ontology.ttl`) keeps only what packages meet at: an action, an agent, the graph kinds.

# How a package is loaded

**Only for a [role](/domain/kernel/role.md) the agent is declared in.** A package is a crate at the
repo's root holding an `ontology.ttl`, named for it (`transport/mqtt` is `orexis-transport-mqtt/`), and that ontology declares the
roles the package serves, beneath `orexis:Role`:

| package | its role | an agent in it |
|---|---|---|
| belief | `belief:Deliberator` | revises what it believes by the rules it holds |
| sensing | `sensing:Observer`, depending on the deliberator | turns its sensors' numbers into observations |
| prediction | `prediction:Predictor` | foresees its readings by the flows |
| planning | `planning:Planner` | derives wants and searches for plans |
| execution | `execution:Executor` | walks intentions and takes their steps |
| speech | `speech:Speaker` | hears its peers' documents and says its own |

The agent's self graph states its roles beside its self, in a domain's words where a domain has them.

**The agent starts every package it holds, and each decides for itself whether it runs.** Two things must agree:
the binary holds the package, a Cargo feature, and the agent's documents call for it. The agent's boot puts the
kernel's vocabulary, the world's documents and the self in the store; then it starts every package, and the first
thing a start does is decide:

| a package | runs where | asked by |
|---|---|---|
| with a role | the self plays a role of its class, or of a domain's class beneath it | `handed.plays(&[ROLE])` |
| a transport | a role the self plays needs bytes and the world wires them through this member | `orexis_transport::wired` |
| keeping house for a role linked to a service | the self plays the role, the role names the service and the world says where it answers | the role the package reads (`Recorder::new`) |

Its own class decides, since no package's role is beneath another package's, and a domain's role class beneath
one is the world's to say, in the store as the boot began. **A package that runs joins, bringing its own documents**
(`handed.joins(&DOCUMENTS)`): its `ontology.ttl` and where it has them its rules and its actions, each a file of its
crate compiled into the binary beside its code and named by it in the order it wants them (`orexis::documents!`),
are put in, and every graph of the world passed over until then, a kind its vocabulary declares, with them, and it
says it joined (`orexis:PackageJoined`). So an agent's store holds the documents of the packages it runs and of no
other. **The order the packages make their cores in is the vocabulary's** ([role](/domain/kernel/role.md)): once
every package has joined or ended its booting, the vocabulary is whole, and a package reads which of the self's roles
its own documents declare and what those depend on (`orexis:dependsOn`), refused where they go round a cycle; it
then waits to hear the end of the booting of each package serving one, since a booting ends saying the roles its
package serves (`orexis:serves`). That the self plays every role depended on is onboarding's to hold. A package whose
role depends on nothing goes straight on; a coordinator makes its core after planning, execution and speech have
made theirs, and no package names another. The package knows its own role; nothing
decides for it, and the kernel names no package, no role and no transport's wiring. Once every start has decided, a
role the self plays that no package of the binary declares is refused, its package having been built out.

**A package's start is the whole of what it does, and its lifecycle is activities inside the agent's**
([the-lifecycle-is-activities-the-packages-hear](/decisions/the-lifecycle-is-activities-the-packages-hear.md)). The
kernel begins the agent's booting (`orexis:AgentBooting`) and, inside it, a booting for every package the binary holds
(`orexis:PackageBooting`): the package decides, joins, makes its core and SAYS IT BOOTED (`handed.booted().await`),
which ends its booting, naming the package (`orexis:package`), and WAITS UNTIL THE AGENT'S BOOTING HAS ENDED, every
package booted or declined and the boot finished, so each is listening before any goes on to speak — and until it
has heard every package's booting ended, since on several threads the agent's may be heard first, and what a
package hears of the others' lifecycle after that wait nothing takes until the agent stops. Where the agent
runs, its running (`orexis:AgentRunning`) holds each package's (`orexis:PackageRunning`), the package's task; where it
is checked, the booting is all there is, and a package told so ends there, having said what the check asks
(`handed.checking()`). Starting the agent ends as its booting does (`Booted::start`, awaited), refused where a package
could not boot. Nothing keeps an order between packages, and nothing knows which run but the events, the lifecycle's
among them. What keeps house for the journal makes its core after the agent has booted, the journal's being made by
then, and what it owes once the others are done it does in its stopping (`handed.stopping()`), inside the agent's
(`orexis:AgentStopping`). What several packages add to is provided as each makes its core (`Provided::alter`) and read once every core
is made (`Provided::share`), as what a chat reads of what happened is. What a caller provides is a package's own
type, a test's journal or a deployment's word that it is deployed, and the binary assembles nothing of it: what a
package makes of what it is handed, and of what it is not, is its own start's to say. The start makes the package's [part](/domain/kernel/part.md) and
goes on as the one task that holds it — a loop of the package's own, awaiting the
[events](/domain/kernel/event.md) beneath its triggers, the kinds of graph written it asked to hear, an arrival
and the clock ([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).

**A package's start is in its crate's `lib.rs`, and nothing else is.** Below what the crate is and its modules: its
registration, the [role](/domain/kernel/role.md) it is loaded for, and `start`, one function from the decision to the
end of its task, the same in every crate. The work is in the modules: the [part](/domain/kernel/part.md) in a file
named for the role, what the package says happened in `events.rs`, and what a test hands it beside what it is
handed to.

**A deployed agent's package makes what it is not handed.** Whoever runs an agent for good hands
`orexis::task::Deployed` outside, and a package then makes its own from what the world says: the journal package
its journal, which it serves and keeps the process's log in (`orexis::task::Said`), and what archives it its
archive on disk. A check and a test do not hand it, so a package handed nothing has nothing, and a check reaches
no disk and no port. What a package owes after every other task has ended, it asks for with `handed.finally`: the
archiver takes there what the others said while stopping.

**A checked agent's package says what the check asks.** Whoever checks an agent hands `orexis::task::Checking`
outside, and a package says there, in its start, whether it holds the agent and why it refuses the world as posed;
planning does where it holds a desire or a constraint the posed state violates, and a transport that listens
says it holds the agent; planning writes its [scopes](/domain/planning/scope.md) in that start too. The binary
reads what was found and asks no package by name. It hands a check no connector either: a transport handed no
member in an agent that is not deployed makes one that reaches nothing.

There is no default set and no fixed mind: an agent declaring no role is joined by the metrics alone. A brought
document's graph is named for its crate and file (`urn:orexis:orexis-sensing/rules.ttl`), a name for eyes. A
crate's `requirements.ttl` is not brought: it is onboarding's, read off the disk by `orexis-onboard`, and no
agent loads it. Onboarding, which is Python and compiles nothing, still finds each crate's documents by looking,
and works out which packages an agent loads from the ontologies, to build its image.


# Whose a word is

**A term lives in the namespace of the package that owns the concept, not of the one that happens
to touch it.** Desires and wants are planning's; an implementation and its operations execution's;
a revision graph belief's. That is why this dictionary is filed by package: a page sits in the
folder of the package that owns its word.

# A domain is not a package

`domains/<name>/` holds a vocabulary, its actions, its shapes and its rules — documents, which a
world imports with `owl:imports` and nothing imports as code ([domain](/domain/kernel/domain.md)).
New behaviour in a world's terms is a domain's to add; a new concern of the agent itself is a
package's.
