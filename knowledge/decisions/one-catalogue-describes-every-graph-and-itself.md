---
type: Decision
title: One catalogue describes every graph and itself
status: accepted
timestamp: 2026-09-19T12:00:00Z
description: >-
  What a graph IS, whose it is, how it arrived, when it holds and what loaded it were said in
  three graphs — a classification graph, a periods graph, a provenance graph — each reader
  naming the one that held its kind of statement. The sovereign's objection was that graph
  metadata was spread over graphs; the question that followed was whether the one graph would
  need a name every reader knows, or would describe itself. It describes itself: one row of the
  catalogue says `a orexis:CatalogueGraph` of the catalogue, the store finds it by asking every
  graph for that row, genesis alone spells its name because genesis creates it, and no reader
  names it. Refused — a well-known name, which is a graph IRI in every reader (rule 1); the
  ontology graph as the place, which is public, so a mention would be a fact in every world;
  and keeping three graphs by kind of statement, which is what the objection was about.
---

# The objection

"Still don't like that graph metadata is spread on different graphs." The store had three
graphs about its graphs. A classification graph said what each per-agent graph IS and whose it
is — written by the graph's owner when it created it, since #708 the one thing code relies on.
A periods graph said when a graph holds — the stretch
[a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md) gives a graph,
read at the door. A provenance graph said what loaded the public graphs, in PROV-O, rewritten
whole at every start. Each was named by a constant; each reader imported the one that held its
kind of statement; and what a graph was said of it was three lookups in three places, which is
the shape a reader gets wrong by forgetting one. The sovereign's next question was the design:
"one graph catalog. Do we still need to know its name? Or this graph will have metadata for
itself?"

# What was decided

**One graph, the catalogue, describes every graph and itself.** A row of it says of a graph its
class or classes, how it arrived (`orexis:arrivedBy`), whose beliefs it holds
(`orexis:beliefsOf`, for a per-agent graph), and when it holds (`dcterms:temporal`, one
`dcterms:PeriodOfTime` with an `orexis:start` and an `orexis:end`); the PROV account of a load
sits beside those rows, in the same graph, in PROV-O and nothing else.

**It describes itself, and that is how it is found.** One row says of the catalogue `a
orexis:CatalogueGraph`. A store opened on a volume asks every graph for the one that says that
of itself — once, and keeps the answer, since nothing moves it — and refuses two, because a
store with two catalogues has two truths about what its graphs are. A store nobody has told
anything to has none, and then has no public knowledge, no own graphs and no periods: the store
it always was. Genesis creates it (`genesis.ensure_catalogue`) and is the one writer that
spells its name, `graph/catalogue`, because the thing that creates a graph has to call it
something. Every other reader and writer takes the name from the door, `store.catalogue`, and
uses it in a `GRAPH` clause: the derivation asking which graphs are of a family, the ledger asking
whether a claim's window has ended.

**A writer classifies what it writes, in the same update.** `Store.classify` writes a row;
`Store.entry` returns the row as the text of a `GRAPH` block, so a writer that creates a graph
and its data in one update puts the row in the same update, and the graph never exists
unclassified for a moment between two writes. A period is part of the row — a want's graph
holds until the want ends, a prediction's during its window — and the same call that types
a graph says when it holds.

**The vocabulary keeps declaring its static graphs, and genesis transcribes them.** A package
says beside its terms that `graph/instruments` is a belief graph that arrives recorded; the
kernel's ontology says the same of the world, the ontology, the desire and the action graphs.
The T-Box is where a package SAYS, and the catalogue is where a reader ASKS: at every start,
after the public graphs are loaded, `genesis.catalogue_public` drops what the catalogue said of
a public graph before and writes what the vocabulary says now, a graph instance being known by
`orexis:arrivedBy`, which the vocabulary states of a graph and of nothing else. So a sixth
public graph is still a vocabulary edit that touches no Python — `tests/test_provenance.py`
holds it there — and the classes a reader asks by are closed over `rdfs:subClassOf` read from
the ontology graphs, so a membership test asks what a graph IS and walks nothing.

**It is not public, and it is not the agent's own.** The store's doors merge the public graphs
as the default graph and hand a search the agent's own beside them; the catalogue is in neither
set. That is the property
[a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md) argued for when
it put the period outside the default union: a description of a graph is a mention, and a
mention that reached the default graph would be a fact in every possible world, constant until
the day it changed, and then a moved invariant. The one exception that record refused — a graph
describing itself — the catalogue takes, and safely, because the catalogue is never handed to
a reader as data; its self-entry answers one question, *which graph is the catalogue*, asked by
the store and by nothing else.

**A deployed volume is gathered once.** A store written when the three graphs existed is
opened, its classification and periods graphs are added into the catalogue and cleared, and its
provenance graph is cleared — the PROV account is rewritten at every start and is not carried.
The three old spellings live in that one migration, `genesis._gather_into_catalogue`, and
nowhere else, since a migration names what it migrates from.

# Refused

**A well-known name.** The catalogue could have kept a constant every reader imports, as the
three graphs had. Refused, because a graph IRI is an instance and rule 1 applies to it: #708 had
just made every other graph nameless to code — a graph's name is for eyes — and the one graph
that says what every graph is would have been the one graph every reader named. Finding it by
its own entry costs one query when a store is opened, cached, and lets the store find its
catalogue the way a reader finds any graph: by what it is.

**The ontology graph.** The T-Box already declared the public graph instances, and a catalogue
could have been that, extended. Refused twice over: the ontology graph is public, so every row
about a graph would be a fact in every world, which is the hazard the period record kept the
meta-graph outside the union to avoid; and a per-agent graph does not exist until its agent
does, so nothing authored before the agent can describe it. The vocabulary's declarations are
where a package says what its graph is; the catalogue is where the store says what its graphs
are, and the two meet by transcription at every start rather than by being one graph.

**Three graphs by kind of statement.** Classification, period and provenance are three kinds of
statement about a graph, and a graph each is a tidy partition. It was the partition the
objection was about: the kinds are a reader's concern only in that a reader has to know which
graph holds which, and the catalogue is one place a reader asks about a graph and gets every
kind of answer. What a row is FOR is said by its predicates; where it sits is not information.

# Seams left open

- **Two lifetimes share the graph, told apart by their writers.** The public rows and the PROV
  account are rewritten at every start; a per-agent row lives as long as its graph. Nothing
  marks a row with which it is: `genesis.catalogue_public` deletes the rows of every graph the
  catalogue has ever called public, and `provenance.describe` the rows in PROV's namespace.
  A third writer that rewrites at start would have to choose its own criterion.
- **The catalogue has no period and is never dropped.** A sweep that drops an ended graph drops
  the graph's rows with it; the catalogue's own row says no stretch, and no sweep reads it.
- **A bare store has no public knowledge until it has a catalogue.** `Store()` answers
  `graphs_of(PUBLIC)` with nothing; a test that builds one and expects a world to be public
  creates the catalogue first, as the package tests' stand-in does. The refusal of two
  catalogues means a volume assembled from two stores fails at the door rather than answering
  from one of them.
