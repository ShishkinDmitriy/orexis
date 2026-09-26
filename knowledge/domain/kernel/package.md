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
