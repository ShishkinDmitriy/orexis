---
type: Domain Concept
title: Metadata
description: >-
  What is said OF a graph rather than by it - its kinds, how it arrived, whose it is, the period it
  holds over, its hash, what it was derived from. Everything else a graph holds is its content. Every
  graph carries its metadata itself and is asked for it there; the catalogue says the same while it
  stands. Told apart by type, never by the graph's name, by each reader of a whole graph where it
  reads: the store hands over triples and knows nothing of the difference.
---

# The two halves of a graph

A graph states facts, and something has to say what that graph is. The first half is its **content**:
the reading, the plan's steps, the round. The second is its **metadata**: every kind it is, the
arrival (`orexis:arrivedBy`), the owner (`orexis:ownedBy`), the stretch (`dcterms:temporal`, one
`dcterms:PeriodOfTime`), the hash of the content (`orexis:hash`) and the graph it was derived from
(`prov:wasDerivedFrom`).

# Where it is said

**By the graph itself, and on its row of the catalogue, the same.** Every writer says both in the one
update that writes the graph: `Store::entry` answers the two blocks, the hash is stamped in both, a
period ended is ended in both under a period node of each's own, and a text that writes a row itself
spells the graph's block beside it. The graph always says `a orexis:Graph` of itself, whatever its
row's kinds close to, since that type is what its metadata is told by.

The metadata is on its way out of the catalogue, so that forgetting a graph is clearing it. A volume
lived in before graphs carried their metadata is brought up as it boots (`Store::carry_metadata`,
which the boot begins with and `close_catalogue` ends with).

# Where it is asked

**Of the graph, in the one `GRAPH` clause a text reads it in.** A text asks a graph what it is, how it
arrived, whose it is and when it holds under the graph's own name, beside the facts it wants of it:

```sparql
GRAPH ?g { ?g a sensing:ObservationGraph ; dcterms:temporal/orexis:start ?from .
           OPTIONAL { ?g dcterms:temporal/orexis:end ?until }
           ?reading sosa:madeBySensor ?sensor }
```

An end that may be missing is asked from the graph by the path, never from the period node a
pattern before it bound: an `OPTIONAL` joined through the period alone is evaluated on its own, every
period of every graph, 12 ms over 6,000 graphs where the path costs a tenth of one, and an
`OPTIONAL` with `OPTIONAL`s inside it 21. `Store::graphs_of` and `revisions_of` ask the engine's
index, one scan of the kind and a lookup under each graph's name, and parse no text.

**What still asks the row** is what reads a package's own word there, and each moves with its word:
a revision's settling, the patterns a copy was cut by, and every text of the search that walks the
cone or reads a weighing. The copy a chat's model queries is still handed the catalogue beside its
graphs, and onboarding's Python reading of a world keeps its own. The catalogue goes after them.

**What a package says of a graph in words of its own is not this.** Whether a revision's rules settled
(`belief:settled`), which patterns a copy was cut by and everything the search knows of a possible
world - the candidate it was made by, what it cost, that it is impossible - stay on the row, each its
package's to move.

**A snapshot case says a graph's metadata once**, on its row: the runner loads the case with every graph
saying the same of itself, holds what a function left to the case with its diff applied and the same
said, and writes a diff with it left out (`orexis/src/snapshots.rs`). A writer that says a
graph's metadata on its row and not in the graph, or the two unalike, leaves a store that differs.

# How the halves are told apart

**By type.** A triple is metadata where its subject is typed, in that same graph, `orexis:Graph` or
`dcterms:PeriodOfTime`; a row carries every kind its class is beneath, so every graph that carries metadata is an
`orexis:Graph`. Not by the graph's name: metadata copied into another graph is no content there
either, and a named node may join the metadata by being typed.

**The store does not know.** It hands over a graph's triples and decides nothing about them, as it
decides no dataset for a reader; a door answering "the content of a graph" was built and taken out
before it merged, a method that knew what every caller wanted. Each reader of a whole graph says the
test itself, in the group it reads the graph in:

```sparql
GRAPH ?w { ?s ?p ?o FILTER NOT EXISTS { ?s a orexis:Graph } FILTER NOT EXISTS { ?s a dcterms:PeriodOfTime } }
```

Two plain filters, since one over a `VALUES` is evaluated per candidate.

A reader that holds a graph's statements in hand, having asked the store for them, says the same by
calling `orexis::metadata::stated` over them, or `stated_quads`: functions over statements, which
ask the store nothing.

# Who asks for the content alone

Only what handles a whole graph as a set of facts, with no type to ask for:

- **the hash** (`orexis/src/hash.rs`) - so a graph hashes alike wherever its metadata is said, and its own
  hash is no part of what is hashed;
- **a fork, and the diff of two graphs** (`orexis-planning/src/fork.rs`, `take.rs`) - a possible world
  is its parent's facts under another name, and what a step changed is what two worlds state, which
  always differ in what each says it is; so with a step's predicted change (`extract_plan.rs`);
- **the cut and the laying of a ground** (`orexis-planning/src/lay_ground.rs`) - what a graph says of
  itself is never cut out of it, and a ground is laid of what the pieces state;
- **a copy into another store** - a plan published and adopted (`publish_plan.rs`,
  `orexis-execution/src/executor.rs`), since the store it lands in says what it is; a graph crossing into
  an imaginarium crosses whole, with its row, being the same graph there;
- **the executor's landing check and a fictive step's write** - the present is held to what a step
  predicted, never to the kind of the graph it was predicted in;
- **belief** - a state graph is emptied when it states nothing, and a revision continued from what
  was concluded (`orexis-belief/src/transition.rs`, `revise.rs`);
- **what is sent or shown** - a statement read back as the document it was said in
  (`orexis-speech/src/statements.rs`), and the copy a chat's model queries, which is handed the
  catalogue beside it (`orexis-translation/src/readable.rs`).

A text that asks for a thing by its class needs nothing: `?r a sosa:Observation` matches no
metadata.

# What follows from it

**A fact whose subject is a graph is never content.** So a thing is never named as the graph it is
written in: a [plan](/domain/planning/plan.md)'s root, a question, an answer and each document a
saying makes go by names of their own.
