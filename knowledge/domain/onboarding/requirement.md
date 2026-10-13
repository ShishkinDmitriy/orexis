---
type: Domain Concept
title: Requirement
term: http://example.org/orexis/onboarding#RequirementGraph
description: >-
  What a world must state of a package's or a domain's words, as SHACL shapes the owner of the
  words ships beside its ontology, in a graph of onboarding's kind. Onboarding holds a world to
  every one before anything is granted; no agent loads one.
---

# What it is

A requirement is a package's word about what a document using its terms must say: a sensor
observes a property and is mounted on something, an observer role reads a sensor, a desire carries
one of its two tests. It is a SHACL shape, and the package or domain owning the words ships it in a
`requirements.ttl` beside its `ontology.ttl`, as `agent/sensing/requirements.ttl` and
`domains/market/requirements.ttl` do. A domain imports it from its ontology, as it imports its
actions and rules.

A requirement is not a [shape](/domain/planning/shape.md) in planning's sense. A met-test says what
an agent wants of the world it believes, and the agent judges it every pass. A requirement says
what a sovereign must have written for the world to be read at all, and it is judged once, before
the world is believed.

# Who reads it

[Onboarding](/domain/onboarding/onboarding.md) alone, which is why the graph's kind is onboarding's,
declared in `onboarding/ontology.ttl` beside the [deployment](/domain/onboarding/deployment.md)
graph's. An agent's boot passes over a kind its vocabulary does not declare, so its store holds no
requirement: what an agent holds is accepted and revised once it runs, and only a sovereign's
document, before it is believed, may be refused.

Onboarding reads the requirements off the world, which knows every package's vocabulary, and holds
the world's common beliefs to them once and each agent's boot to them per agent. It never reads them
off an agent's boot, which loads only what the agent's roles do: an agent playing an executor alone
loads no planning, and the requirement refusing it is planning's.

# What stays in the ontology

What an agent reads as it runs stays in the vocabulary it loads. The observer's limits are the one
case: what holds of `sensing:silentAfter` and `sensing:stuckAfter` where a role states none is a
`sh:defaultValue` on a shape in sensing's ontology, which the stuck rule reads there. That shape
refuses nothing; the observer's refusals are its requirement's.
