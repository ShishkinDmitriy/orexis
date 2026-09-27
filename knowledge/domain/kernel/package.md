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

**Belief, planning and execution are the mind, and every agent has them.** Any other package is
loaded — its documents put in the store, its modules imported — only where its **premise** holds:
an ASK over the world's public graphs with `$me` bound to the agent, written in `PREMISES` in
`agent/runtime.py`. A premise answers in advance what the package's callers will read, so it is
in their words:

| package | its premise holds where |
|---|---|
| sensing | a sensor is hosted by what the agent acts for, or by a sample of it |
| prediction | such a sensor exists and a `prediction:Drift` is declared |
| speech | the agent `mqtt4ssn:listensToTopic` a topic, or an action holds an `execution:Saying` |
| the MQTT transport | the agent listens to a topic, or a sensor of its `mqtt4ssn:observesTopic` one |

The premise is the runtime's to state and not the package's, because speech's is spoken in the
transport's words and in execution's, which speech's layout test forbids it as a layer above, and
because what a premise decides is an `import` the runtime or the transport makes. Nothing is declared by the
agent: its own file naming its packages was refused as a second source beside the world
([a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md)).

**A premise is read before its package is.** The boot puts in the kernel, the mind and the world,
finds the agent, asks each premise, and only then reads the documents of the packages that
held — so a premise may read nothing but the kernel's and the mind's kinds, and a word it names
(`prediction:Drift`) is matched as the IRI it is, with no vocabulary behind it yet. A domain that
speaks a package's words, as climate's drifts speak prediction's, is read whether the package
is loaded or not. A package directory that is neither the mind nor listed with a premise is read
by no agent, and `agent/tests/test_premises.py` fails on one.

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
