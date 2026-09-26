---
type: Repository
title: Belief base
description: >-
  One agent's store - a pyoxigraph store in a volume of its own, holding every graph the agent
  knows, each described by one catalogue graph that says what it is, whose, how it arrived and
  when it holds. Built at the first boot from its world's documents and kept; nothing else can
  open it.
---

# What it is

A quad store, and in it named graphs: the vocabulary and the closure, the world's public
documents, the state the agent observes and what the rules conclude of it, the predictions, the
desires and wants, the records, the intentions. **There is no shared store.** Each agent's is a
file in its own volume, built from the ratified documents of `world/<world>/`, so isolation is
structural: nothing needs enforcing because nothing else can open it.

# The catalogue

One graph describes every graph, itself included, and is found by its own row, `a
orexis:CatalogueGraph`. Per graph it says:

- **what it is** — its kind, and every kind that kind is beneath ([modality](/domain/kernel/modality.md));
- **whose it is** — `orexis:beliefsOf`, the owner that created it; a graph saying none is nobody's;
- **how it arrived** — `orexis:arrivedBy`, one of Asserted, Derived, Received, Recorded;
- **when it holds** — `orexis:start` and `orexis:end`, a period; absent is always.

A reader states the kinds it reads and the instant it stands at, `store.graphs_of` answers with the
graphs, and the query is handed exactly those as its default graph. The store decides nothing for
a caller, and a graph's NAME is for eyes: code relies on its row alone.

# What lives beside it

Each reading also goes to the agent's bucket as a series point, for the panels to draw. The
series is watched, never believed: nothing reads it back into the store.

# What a restart keeps

Everything the agent owns. A volume it has lived in re-reads only the documents nobody owns — the
ontologies, the domains, the world's public graphs — so an updated vocabulary reaches it and its
own beliefs are never reset by a restart.
