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
| sensing | `sensing:Observer`, beneath the deliberator | turns its sensors' numbers into observations |
| prediction | `prediction:Predictor` | foresees its readings by the flows |
| planning | `planning:Planner` | derives wants and searches for plans |
| execution | `execution:Executor` | walks intentions and takes their steps |
| speech | `speech:Speaker` | hears its peers' documents and says its own |

The agent's self graph states its roles beside its self, in a domain's words where a domain has them.

**The agent starts every package it holds, and each decides for itself whether it runs.** Two things must agree:
the binary holds the package, a Cargo feature, and the agent's documents call for it. The agent's boot puts the
documents of every package the binary holds in the store, its `ontology.ttl` and where it has them its rules and
its actions, each a file of its crate compiled into the binary beside its code (`orexis::documents!` in the crate's
registration), whether or not the package runs; then it starts every package, and the first thing a start does is
decide:

| a package | runs where | asked by |
|---|---|---|
| with a role | the self plays a role of its class, or of a class an ontology in the store puts beneath it | `handed.plays(&[ROLE])` |
| a transport | a role the self plays needs bytes and the world wires them through this member | `boot::wired` |
| keeping house for a role linked to a service | the self plays the role, the role names the service and the world says where it answers | the role the package reads (`Recorder::new`) |

One look decides, since every package's ontology is in the store before any start: a translator is a speaker by
translation's, so speech runs for a translator whether or not translation has looked yet. The package knows its own
role; nothing decides for it, and the kernel names no package, no role and no transport's wiring. A role the self
plays that no package of the binary declares is refused, its package having been built out. A deployed image is
built with its agent's packages alone (`orexis-compose`), so its store holds their documents and no other's.

**A package's start is the whole of what it does, and its lifecycle is two events.** It decides, makes its core,
SAYS IT HAS STARTED (`handed.started("belief").await`), and checked (`handed.checking()`), ends there: each package
checks its own; otherwise it goes on as its task. Saying it started WAITS UNTIL EVERY PACKAGE HAS MADE ITS CORE OR
ENDED, so each is listening before any goes on to speak, and then says `orexis:PackageStarting` and
`orexis:PackageStarted`, at the instants it began and made its core and naming the package (`orexis:package`), so the
journal, made by then, keeps every start. Starting the agent ends there too (`Booted::start`, awaited): once every
package has made its core or ended, refused where one could not be made. Nothing keeps an order between packages, and nothing knows which run but
the events. What keeps house for the journal makes its core after saying it started, the journal's being made by
then. What several packages add to or read is shared outside (`Outside::share`) and asked when it is read, as where
the journal lies is. The start makes the package's [part](/domain/kernel/part.md) and
goes on as the one task that holds it — a loop of the package's own, awaiting the
[events](/domain/kernel/event.md) beneath its triggers, the kinds of graph written it asked to hear, an arrival
and the clock ([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).

**A package's start is in its crate's `lib.rs`.** Below what the crate is and its modules: what a test hands it, the
[role](/domain/kernel/role.md) it is loaded for, its registration, `start`, `make` and its task, the same in every
crate. The work is in the modules.

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
