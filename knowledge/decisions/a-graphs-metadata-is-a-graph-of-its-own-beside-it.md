---
type: Decision
title: A graph's metadata is a graph of its own beside it
status: accepted
timestamp: 2026-11-21T18:00:00Z
description: >-
  What a graph is - its kinds, owner, arrival, period, hash, derivation, and what a package says of
  it - is said in a metadata graph of its own, one per graph, linked to it by `orexis:metadataOf`.
  The graph holds its facts alone. Refused, each after it was built - one catalogue describing every
  graph, and metadata inside the graph told from its facts by type. The rows of a search, which are
  no graph's metadata, go in one cone graph per imaginarium.
---

# The question

One catalogue said what every graph is
([one-catalogue-describes-every-graph-and-itself](/decisions/one-catalogue-describes-every-graph-and-itself.md)).
It was to be retired, so that forgetting a graph is clearing it and a copy into an
[imaginarium](/domain/planning/imaginarium.md) carries what the graph is with it. Where the
metadata goes instead had three answers, and two were built before the third was taken.

# What was decided

**Each graph has a metadata graph of its own.** An `orexis:MetadataGraph` says of itself that it is
one and which graph it is of, and of that graph everything the catalogue row said. The sovereign put
it as splitting the one big catalogue into a small graph per data graph. Nothing describes a
metadata graph in turn. A reader finds one by the link, never by its name
([metadata](/domain/kernel/metadata.md)).

**The rows of a search are in one graph.** The candidates, the weighings, the path between possible
worlds and each ground's derivation from the ground before are not metadata of any graph: they are
asked across every world at once and walked as paths, and a path is walked inside one graph. They
are a `planning:ConeGraph`, one per imaginarium ([cone](/domain/planning/cone.md)).

# What was refused

**The catalogue kept.** Every text had to find it first, forgetting a graph meant finding its rows,
and a copy picked rows out of it. Measured over 6,000 graphs it costs what the metadata graphs
cost, so nothing was lost by leaving it.

**Metadata inside the graph, told from its facts by type.** Built and merged in two steps: a triple
whose subject its graph typed `orexis:Graph` or `dcterms:PeriodOfTime` was metadata, and every
reader of a whole graph filtered it. It worked, and it made a graph two things. The hash read
triples it then discarded, a graph of six facts hashing in twice the time; a fork, a diff, a cut
and a copy each had to say the filter; and a fact about the graph itself could no longer be stated
in it. With the metadata beside the graph none of them asks anything.

**A package's word about a graph in the cone graph, or the search's rows in each world's
metadata.** `belief:settled` and `planning:cutBy` are said of one graph and read with it, so they
are metadata. A world's path is read with every other world's, so it is not.

# Seams left open

- **A reader may not name a metadata graph, and nothing checks that a graph has one only.** Two
  graphs saying they are the metadata of one graph would both be read.
- **A volume lived in while the catalogue stood is brought over at boot and never back.** The boot
  names the retired class by its IRI, which no vocabulary declares any more.
- **A cone graph emptied is still said to be one**: its metadata graph stays when its last row
  goes, as an emptied belief's does.
