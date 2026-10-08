---
type: Domain Concept
title: Package
description: >-
  A directory of `agent/` that owns a concern and the words for it — belief, sensing, prediction,
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
| `agent/belief/` | revision: the rules a store holds, run over what was written |
| `agent/sensing/` | an instrument's bytes become an observation |
| `agent/prediction/` | when a reading will change range |
| `agent/planning/` | desires and wants, the search, the plan |
| `agent/execution/` | intentions, taking a step, the world's answer |
| `agent/speech/` | a peer's document heard, the agent's own said |
| `agent/transport/` | reaching the society; MQTT is the member that ships |

`agent/runtime.py` is the container that assembles them, and the kernel's `orexis:` vocabulary
(`agent/ontology.ttl`) keeps only what packages meet at: an action, an agent, the graph kinds.

# How a package is loaded

**Only for a [role](/domain/kernel/role.md) the agent is declared in.** A package is a directory of
`agent/` holding an `ontology.ttl`, found by looking and never listed, and that ontology declares the
roles the package serves, beneath `orexis:Role`:

| package | its role | an agent in it |
|---|---|---|
| belief | `belief:Deliberator` | revises what it believes by the rules it holds |
| sensing | `sensing:Observer`, beneath the deliberator | turns its sensors' numbers into observations |
| prediction | `prediction:Predictor` | foresees its readings by the drifts |
| planning | `planning:Planner` | derives wants and searches for plans |
| execution | `execution:Executor` | walks intentions and takes their steps |
| speech | `speech:Speaker` | hears its peers' documents and says its own |

The agent's self graph states its roles beside its self, in a domain's words where a domain has them.
The boot reads the kernel and the world, finds the agent and puts its self graph in, then closes the
declared roles over `rdfs:subClassOf` — the steps the world's domains state, and each package's own,
read off its ontology APART from the store — and loads exactly the packages whose ontology declares a
role in that closure, its documents put in and its part created. A package's ontology never enters an
agent's store to answer whether the package is needed: Hanoi's mover, a planner and an executor,
holds no sensing, prediction, speech or belief document, as the #824 measurement found. A domain that
speaks a package's words, as climate's drifts speak prediction's, is read whether the package is
loaded or not.

**A transport is no role.** It is loaded where a loaded role needs bytes and the society wires a bus
— the MQTT member for an observer one of whose sensors publishes on a topic, or a speaker that
listens to one; the HTTP member for an observer one of whose sensors is a thing with a form —
asked over the world's public graphs and the self (`TRANSPORTS` in `agent/runtime.py`). That is the
one derivation left, since which bus reaches a device is wiring and not a choice. History and metrics
are loaded from the environment.

There is no default set and no fixed mind: an agent declaring no role loads nothing. A package
directory with no `ontology.ttl` is no package and is read by no agent, and one whose ontology
declares no role is read by none but as a transport; `agent/tests/test_roles.py` holds the tree to
both, and every role both ways — declared, loaded and its part created; undeclared, absent.

Once loaded, a package **starts itself**: `agent/<package>/create.py` exports `create(runtime)`, which
makes the package's [part](/domain/kernel/part.md); the parts are linked to each other, then started,
each saying what its package does by jobs, timers and [signals](/domain/kernel/signal.md), and the
runtime calls them knowing no word of what they do ([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)).

A package's need of another is said by its role sitting beneath the other's — the observer beneath
the deliberator, since an observation's sides are revisions — in the package's own ontology, so no
package speaks a word above it and the runtime knows none of the needs
([a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md)).

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
