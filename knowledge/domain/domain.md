---
type: Domain Concept
title: Domain
description: >-
  A body of knowledge several worlds can pose — its words, its actions and what its words mean
  when wanted — kept in `domains/<name>/` in Agent 0.2.0 and imported by a world that speaks it.
  Hanoi and the courier grid are the two that ship.
---

# What it is

A **domain** is what a world poses an instance of: the Tower of Hanoi, a courier on a grid, and
in time the plant's water and climate. It is the knowledge that does not change from one
instance to the next — the words a world describes its things in, the actions an agent can take
on them, and what those words mean when wanted — where a [world](/domain/world.md) holds the
instance: its agents, its individuals, its desires and the state it starts from. The project's
opening claim, that the plant is the example and not the architecture, is the claim that a domain
is a plug-in (the-domain-is-a-plug-in-and-hanoi-is-the-proof).

In Agent 0.2.0 a domain is a directory, `domains/<name>/`, of three documents, each saying which
graph it is:

| document | graph kind | holds |
|---|---|---|
| `ontology.ttl` | `orexis:OntologyGraph` | the classes and properties, the domain's invariant individuals (Hanoi's pegs), the parameters its actions take — and `owl:imports` of the other two |
| `actions.ttl` | `orexis:ActionGraph` | its actions, each with what it takes, when it is available, what it costs and what it adds and retracts |
| `shapes.ttl` | `orexis:ShapesGraph` | what its words mean when wanted — a met-test shape a desire's `orexis:metWhen` points at, and the select its `orexis:estimates` points at |

The planner reads actions from action graphs alone, not from every public graph. The measures sit with the actions because *never overstates* is a promise about the domain's own
costs, which no world can keep. A shapes graph is its own kind, crossed by the
[planner](/domain/planner.md) beside the graphs of desires, wants and records, so that a pass
reads a met-test without reading every vocabulary.

# How a world uses one

A world imports it: `owl:imports <../../domains/hanoi/ontology.ttl>` on a world document's own
`<>`. A relative IRI resolves to the domain document's `file:` IRI, which is the name its graph is
loaded under, so the import names the graph it brings; the [runtime](/domain/runtime.md) follows
imports transitively when it boots, and loads only the domains a world asks for — a courier world
holds no Hanoi move in its scopes. A world whose words are its own alone may keep them beside its
files instead; a vocabulary two worlds speak is a domain.

A domain carries no Python and is no distribution: what it declares is data, and nothing imports
it. The 0.1.0 tree's `packages/orexis-tool-*` were the same knowledge as packages, and stay while
a 0.1.0 world still loads them.
