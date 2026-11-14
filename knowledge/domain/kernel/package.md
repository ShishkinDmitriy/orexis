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

**A package decides for itself whether the agent runs it, in its own start.** Two things must agree: the
binary holds the package, a Cargo feature, and the agent's documents call for it. Where either says no, it is
not loaded. Every package the binary holds is given its start, and the first thing a start does is decide:

| a package | joins where | asked by |
|---|---|---|
| with a role | the self plays a role of its class, or of a class an ontology in the store puts beneath it | `handed.plays(&[ROLE])` |
| a transport | a role the self plays needs bytes and the world wires them through this member | `handed.joins(...)` over `boot::wired` |
| keeping house for another | that package joined | `handed.beside("sensing")` |
| keeping house for a role linked to a service | that package joined, the role names the service and the world says where it answers | `handed.joins(...)` over `boot::connected` |
| the metrics | always | `handed.joins(|_| Ok(true))` |

The package knows its own role; the kernel names no package, no role and no transport's wiring. A package that
joins **brings its documents**: its `ontology.ttl`, and where it has them its rules and its actions, each a file
of its crate compiled into the binary beside its code (`orexis::documents!` in the crate's registration). They are
put in the store, the vocabulary is closed again, and every graph of the world passed over until then is offered
again, since a kind this package declares is now one the agent reads.

**The asking goes round until it settles.** A package that joins may bring the ontology that puts a role beneath
another's: translation's says a translator is a speaker, so speech, asked before translation joined, is asked
again after. A round in which nobody joined settles it, and those still asking decline. So a package's ontology
enters the store only where the package joined: Hanoi's mover, a planner and a recorder, holds no execution,
sensing, prediction, speech or belief document. A role the self plays that no package of the binary declares is
refused, its package having been built out. A domain that speaks a package's words, as climate's flows speak
prediction's, is read whether the package is loaded or not.

**Then each start goes on, in the order the packages start, and its lifecycle is two events.** The kernel says
`orexis:PackageStarting` as a joined package's start is resumed and `orexis:PackageStarted` as it ends, each
naming the package (`orexis:package`), so the journal keeps which packages run. A package whose start needs what
another's made waits for that one: translation waits for speech (`handed.started("speech")`), and what keeps
house for the journal waits for the journal. The start makes the package's [part](/domain/kernel/part.md) and
answers the one task that holds it — a loop of the package's own, awaiting the
[events](/domain/kernel/event.md) beneath its triggers, the kinds of graph written it asked to hear, an arrival
and the clock ([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).

**A start does nothing before it has joined.** The boot runs every start as far as its decision and drops it
there (`task::decide`), so that whoever runs the agent knows what joined before anything is made — the journal
is created only for a recorder — and `task::start` runs the starts of the joined to their ends.

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
