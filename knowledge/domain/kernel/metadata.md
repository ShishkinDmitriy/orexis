---
type: Domain Concept
title: Metadata
term: http://example.org/orexis#MetadataGraph
description: >-
  What is said OF a graph rather than by it - its kinds, how it arrived, whose it is, the period it
  holds over, its hash, what it was derived from, and what a package says of it. Said in a graph of
  its own beside the graph, its metadata graph, one per graph, found by the link it states. A graph
  therefore holds its facts and nothing else, and no reader tells the two apart.
---

# The two graphs

A graph states facts, and something has to say what that graph is. The facts are the graph: the
reading, the plan's steps, the round. What the graph IS is its **metadata**: every kind it is, the
arrival (`orexis:arrivedBy`), the owner (`orexis:ownedBy`), the stretch (`dcterms:temporal`, one
`dcterms:PeriodOfTime`), the hash of what it holds (`orexis:hash`), the graph it was derived from
(`prov:wasDerivedFrom`), and whatever a package says of the graph in words of its own - whether a
revision's rules settled (`belief:settled`), which patterns a copy was cut by (`planning:cutBy`).

# Where it is said

**In the graph's metadata graph**, an `orexis:MetadataGraph`: one per graph, written by whoever
creates the graph, and gone with it. It says of itself two things and no more, that it is one and
which graph it is of:

```turtle
GRAPH :sensed.metadata {
  :sensed.metadata a orexis:MetadataGraph ; orexis:metadataOf :sensed .
  :sensed a orexis:BeliefGraph , orexis:Graph ; orexis:ownedBy :keeper ; orexis:hash "sha256:…" .
}
```

Nothing describes a metadata graph in turn, so there is no graph of graphs of graphs. A writer names
a new one after its graph (`orexis::metadata::named`); a reader never relies on that name and finds
it by `orexis:metadataOf` (`Store::metadata_of`).

`Store::entry` answers the block a text puts beside the graph's own in one update, `Store::classify`
writes it, and `hash_named_graph` stamps the hash there. `Store::forget_graph` clears the graph and
its metadata graph together, and whatever copies a graph into another store copies both.

# Where it is asked

**In a block of its own, beside the block that reads the facts.** A text asks what a graph is, how
it arrived, whose it is and when it holds of whichever graph says so, and the facts of the graph
itself:

```sparql
GRAPH ?m { ?g a sensing:ObservationGraph ; dcterms:temporal/orexis:start ?from .
           OPTIONAL { ?g dcterms:temporal/orexis:end ?until } }
GRAPH ?g { ?reading sosa:madeBySensor ?sensor }
```

An end that may be missing is asked from the graph by the path, never from the period node a
pattern before it bound: an `OPTIONAL` joined through the period alone is evaluated on its own, every
period of every graph, 12 ms over 6,000 graphs where the path costs a tenth of one. Measured over
6,000 graphs, the two blocks cost what one catalogue cost and what metadata inside the graph cost,
0.03 ms for a kind and 0.4 ms with a period and facts.

Code asks the engine's index and parses no text: `Store::graphs_of` and `revisions_of` scan the
kind and keep what a metadata graph says of the graph it is of, `kinds_of` and `said_of` answer one
graph's.

# What it replaced

**One catalogue**, a graph that said what every graph is, itself included
([one-catalogue-describes-every-graph-and-itself](/decisions/one-catalogue-describes-every-graph-and-itself.md)).
Forgetting a graph meant finding its rows, a copy into an imaginarium picked rows out, and every
text had to find the catalogue first. A volume lived in while it stood is brought over as it boots
(`orexis/src/boot.rs`).

**Metadata inside the graph**, told from its facts by type, was built next and taken out: every
reader of a whole graph had to filter it, the hash read triples it then discarded, and a graph of
six facts hashed in twice the time. With the metadata beside the graph, a graph is hashed, forked,
diffed, cut and copied whole.

# What follows from it

**A snapshot case says every graph it holds**, the metadata graph of each beside it, so a function
that writes a graph and not what it is leaves a store that differs (`orexis/src/snapshots.rs`).

**A thing is still never named as the graph it is written in.** A [plan](/domain/planning/plan.md)'s
root, a question, an answer and each document a saying makes go by names of their own, so a fact
under a graph's name is never about two things.

**The rows of a search are not metadata.** The candidates, the weighings and the path between the
possible worlds of an [imaginarium](/domain/planning/imaginarium.md) are asked across every world
at once, so they are written in one graph, the search's [cone](/domain/planning/cone.md) graph; what
each world is, its kind, its period and its hash, is in that world's metadata graph as of any graph.
