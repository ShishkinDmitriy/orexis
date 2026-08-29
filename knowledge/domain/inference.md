---
type: Service
title: Inference
description: >-
  The service that materialises what the vocabulary entails, so both engines read one graph and
  no query walks a subclass path by hand. It writes into graphs whose TYPE is the same as their
  source's — the arrival axis is what tells them apart, which is the one place the type-alone
  convention is not enough.
---

# What it runs

**Entailment materialisation**, at genesis and before any derivation rule. Twenty-five declared
axioms become asserted triples: subclass and subproperty closure over the vocabulary, then the
same over the instances a world states.

# What it reads and writes

![inference — what it reads and writes](../diagrams/service-inference.svg)

**A type does not distinguish these, and the arrival does.** `graph/ontology` and
`graph/ontology/entailed` are both `ag:OntologyGraph`; what separates them is `ag:arrivedBy`. So
a diagram that names graphs by type must carry arrival beside it wherever a service writes back
into the type it read.

# Why it runs first

Order is the point: a derivation rule may then ask what a thing IS rather than spelling out a
subclass path, because by the time it runs the answer is asserted. Widening belongs here rather
than in a query — `tests/test_inference.py` refuses a seventh hand-rolled walk.
