---
type: Decision
title: "A desire is a shape, and the graph it sits in says whose it is"
description: The sovereign's proposal, and it supersedes the desired-state design of a day
  earlier — store what an agent pursues as SHACL rather than as data. Constraint, desire and
  obligation become one language differing in severity and in whose graph they sit; a shape
  is a template so silence means "no constraint" instead of being ambiguous; and the SHACL
  hazard the desired-state design created is closed by construction, since a want that is not
  in the data graph cannot be mistaken for a fact. Measured before recording: custom severity
  survives the engine, instance targeting is native, and one shape covers every property a
  subject states a range for.
---

# A desire is a shape, and the graph it sits in says whose it is

A day of design converged, then turned over one more time. The frame said the graph carries
the modality, so a goal could be belief-shaped triples in a desire graph — and that was right
enough to be worth recording and wrong in a way the sovereign spotted immediately: **why
invent a way to say "the world should look like this" when SHACL is one?**

[a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md) had already
written *"SHACL shapes are already desired graphs"* and nobody had taken it literally.

## What it collapses

Both halves of what we had been calling a region become the same language, differing only in
force and in whose graph they are in:

```turtle
# the sovereign's, ratified — violating is illegitimate
[ sh:targetNode :fern ; sh:severity sh:Violation ;
  sh:property [ sh:path …moisture ; sh:minInclusive 0.20 ; sh:maxInclusive 0.85 ] ]

# the agent's, chosen — violating is a GAP
[ sh:targetNode :fern ; sh:severity ag:ShouldBecome ;
  sh:property [ sh:path …moisture ; sh:minInclusive 0.45 ; sh:maxInclusive 0.65 ] ]
```

`ag:Bounds`, `ag:boundedBy` and `ag:Aim` retire — and with them the argument we had been having
for two days about what to call a thing that binds and motivates at once. It binds at
`sh:Violation` and motivates at `ag:ShouldBecome`, and an obligation is the same shape again,
sourced by a peer's claim rather than by the sovereign or the agent.

**Graphs keep provenance; shapes carry content.** Two axes, and the sovereign's phrasing is the
one to keep: *keep graphs to keep prov, but inside graphs we have shapes*. The graph says whose
it is and how it arrived; the severity says what force it has.

## What it fixes that the desired-state design did not

- **The SHACL hazard closes by construction.** Desired states shared belief's shape, so a
  shape asking "is there an observation of moisture for fern" would have been satisfied by
  the WANTED one — and validation is the worst place for a false positive, being the layer
  that refuses illegitimate worlds. A want that is not in the data graph cannot be mistaken
  for a fact.
- **Silence stops being ambiguous.** In a desired-state graph, a missing triple could mean "I
  do not care about this property" or "this want is unmet". A shape constrains only what it
  mentions, so silence means no constraint — *a shape is a template, not all of it must be
  filled*, which is the sovereign's own formulation and the sharpest argument of the lot.
- **Continuous desires become satisfiable.** A desired state of exactly 0.55 is never reached,
  so "satisfied" needs a tolerance invented somewhere; a shape with a range is simply MET.
  The band machinery this project built by hand is what a shape says natively.
- **Pattern goals need no new vocabulary.** "This claim discharged" is a shape with a target
  and a property constraint — which is what an obligation driving an act requires, and what
  the reflex could never express while it knew only property-and-value.

## Measured before recording

Three things the design rests on, checked rather than assumed:

- **Custom severity survives the engine.** A result came back carrying `ag:ShouldBecome`, so
  force is expressible. And the filter that makes it usable already exists: `conforms()` was
  written months ago to let warnings through because pyshacl reports non-conformance for ANY
  result, so an unmet desire will not stop an agent from booting — machinery built for one
  reason turning out to be the machinery this needs.
- **Instance targeting is native** — `sh:targetNode <fern>`, no per-type indirection.
- **One shape covers every property a subject states a range for**, quantified rather than
  enumerated, and its report IS the gap: focus node, property, value, bounds.

## The split that follows: declarative for steering, SPARQL for the rest

The two shape flavours differ in whether anything but the engine can read them, and that
decides where each belongs:

- **Declarative** (`sh:property` with `sh:minInclusive`) — the numbers are ordinary RDF, so
  urgency reads them with a query exactly as it reads `ag:Bounds` today. This is what the hot
  path uses: a gap is computed on every reading, and running a validator there would be
  orders of magnitude slower for no gain.
- **`sh:sparql`** — expressive enough for the all-properties form and for pattern goals, but
  its numbers live inside a query string where nothing but the engine can reach them. So these
  are evaluated on the keeper's clock or on demand, never per reading.

That gives the *profile of pursuable goals* a concrete meaning: **a goal the reflex must steer
by is declarative; a goal that is merely checkable may be anything.** Without the profile an
agent could hold goals nothing could ever plan for, and the failure would be silence.

# Seams left open

- **Shape versus shape has no operator.** "The agent's aim sits inside the sovereign's bounds"
  is containment, and SHACL has none. The answer is the one that saves the hot path — shapes
  are RDF, so a plain query compares the agent's `sh:minInclusive` against the sovereign's.
  It works and it is mind-bending to read: SHACL validated by a query over SHACL. Worth
  meeting on purpose rather than by surprise.
- **What a runtime-authored shape may contain.** An agent minting a shape is minting data, not
  code, so nothing is unsafe — but nothing yet says which constructs a *received* shape may
  use, and an obligation arrives from a peer. The profile above is the start of that answer,
  not the whole of it.
- **Whether an agent may hold a `sh:Violation` shape about itself.** Self-binding is
  expressible and nobody has decided whether it should be legal; the mandate machinery says
  what an agent may not do, and this would let an agent say it too.
- **The validator still flattens.** SHACL sees one merged graph, so which graph a shape came
  from is lost at validation time — fine while shapes and data are different kinds of thing,
  and the reason this design is safer than the one it supersedes. It becomes a question again
  the day something wants to validate the shapes themselves per source.
