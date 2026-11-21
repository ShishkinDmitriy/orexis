---
type: Domain Concept
title: Description
description: >-
  What is said OF a graph rather than by it - its kinds, how it arrived, whose it is, the period it
  holds over, its hash. Everything else a graph holds is its content. Told apart by type, never by
  the graph's name, and by each reader of a whole graph in its own text: the store hands over
  triples and knows nothing of the difference.
---

# The two halves of a graph

A graph states facts, and something has to say what that graph is. The first half is its **content**:
the reading, the plan's steps, the round. The second is its **description**: every kind it is, the
arrival (`orexis:arrivedBy`), the owner (`orexis:ownedBy`), the stretch (`dcterms:temporal`, one
`dcterms:PeriodOfTime`) and the hash of the content (`orexis:hash`).

Today the description is a row of the catalogue, a graph apart. It is on its way into the graph it
describes, so that forgetting a graph is clearing it and a text asks a graph what it is in the one
`GRAPH` clause it reads it in. Until every writer and reader has moved, a description may lie in
either place, and nothing may depend on which.

# How the halves are told apart

**By type.** A triple is description where its subject is typed, in that same graph, `orexis:Graph` or
`dcterms:PeriodOfTime`; a row carries every kind its class is beneath, so every described graph is an
`orexis:Graph`. Not by the graph's name: a description copied into another graph is no content there
either, and a named node may join the description by being typed.

**The store does not know.** It hands over a graph's triples and decides nothing about them, as it
decides no dataset for a reader; a door answering "the content of a graph" was built and taken out
before it merged, a method that knew what every caller wanted. Each reader of a whole graph says the
test itself, in the group it reads the graph in:

```sparql
GRAPH ?w { ?s ?p ?o FILTER NOT EXISTS { ?s a orexis:Graph } FILTER NOT EXISTS { ?s a dcterms:PeriodOfTime } }
```

Two plain filters, since one over a `VALUES` is evaluated per candidate.

# Who asks for the content alone

Only what handles a whole graph as a set of facts, with no type to ask for:

- **the hash** (`orexis/src/hash.rs`), which says it in code, being no text - so a graph hashes alike
  wherever it is described, and its own hash is no part of what is hashed;
- **a step's predicted change** (`orexis-planning/src/extract_plan.rs`) - the diff of two possible
  worlds, which always differ in what each says it is;
- **the executor's landing check and a fictive step's write** (`orexis-execution/src/executor.rs`) -
  the present is held to what a step predicted, never to the kind of the graph it was predicted in.

A text that asks for a thing by its class needs nothing: `?r a sosa:Observation` matches no
description.

# What follows from it

**A fact whose subject is a graph is never content.** So a thing is never named as the graph it is
written in: a [plan](/domain/planning/plan.md)'s root, a question, an answer and each document a
saying makes go by names of their own.
