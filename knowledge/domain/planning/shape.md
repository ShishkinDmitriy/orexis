---
type: Domain Concept
title: Shape
term: http://example.org/orexis/planning#ShapesGraph
description: >-
  SHACL, as this project says "I want" - a met-test is a node shape a desire or a want points at
  with `planning:metWhen`, declared by a domain in a `planning:ShapesGraph` beside the selects its
  estimates point at. A shape is never run as validation here - it is compiled to the select
  whose rows are its violations, and the search reads those.
---

# What it is

A domain declares what its words mean when wanted. Hanoi's `hanoi:solved` says every disk's
chain bottoms out on peg C; climate's shapes say a subject's soil is `inside` its operating range.
A world's desire points at one:

```turtle
:every_disk_home a planning:Want ; planning:metWhen hanoi:solved ; planning:estimates hanoi:disksAstray .
```

The shapes live in `domains/<name>/shapes.ttl`, a graph that says it is a `planning:ShapesGraph`,
its own kind so that the planner crosses the shapes into a pass without every ontology.

# How it is read

`violation.py` compiles a shape to one SELECT whose rows are its violations — the focus node, the
constraint it broke, what the constraint is about, and the value that offended where the
constraint has one (`planning:offending`, the reading that is below) — and `weigh` runs it in a
world and writes the rows as `planning:violation`s on the weighing. No row is met. A shape's `sh:sparql` constraint
carries its own select and its own prefixes; one a [refinement](/domain/planning/refinement.md)
mints is exactly that, the bridge's WHERE bound and negated.

A met-test is a boolean by nature. How far a world still is belongs to `planning:estimates`, a
separate select the domain promises never overstates, which orders the frontier and judges nothing.
