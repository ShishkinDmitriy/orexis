---
type: Decision
title: A reader states the kinds it reads, and the store decides nothing
status: accepted
timestamp: 2026-09-19T17:00:00Z
description: >-
  The store had four read doors, each assembling a dataset by a rule of its own, and which
  graphs were the agent's own was a set of five kernel classes the store excluded and a class
  tree it walked — so a package chose how the store would treat its graph by which class it
  subclassed, and a caller never said what it read. The sovereign's objection was a method that
  knows the whole system. The read side is the engine's now: a query is handed its graphs, a
  reader asks the catalogue for the graphs of the kinds it names at the instant it stands at, a
  text that reads one graph names its kinds in SPARQL by joining the catalogue, and every row
  carries every kind its class is beneath so no path is walked. Refused — the union of all
  graphs as the default, a default dataset in the store, and treatment by subclass.
---

# The objection

"We made a method that knows the whole system." The store's read side was four doors.
`query` merged the public graphs as the default graph. `query_at` merged public, the agent's
own and the predictions holding at an instant, with the state graph swapped for a possible
world. `query_union` read everything. `query_over` took names. What "the agent's own" meant
was a rule of the store's: every graph typed under `orexis:Graph` whose classes met none of
five — public, possible, working, prediction, the catalogue — closed over the vocabulary's
`rdfs:subClassOf`. So a package decided how the store would treat its graph by which kernel
class it put its own under: `WorkingGraph` to be hidden from every rule, `RecordGraph` to be
carried as it stands, nothing to be carried at an instant. A class under none was a graph no
door handed out, and nothing said so. Measured on a store with four fresh classes, one under
each: carried, hidden, public, invisible.

The second half of the objection was the caller. A reader taking `query_at` did not know what
it read; the door knew, and the door's knowledge was the class tree. "Why can't the caller
know? You have type."

# What was decided

**A query is handed its graphs.** `store.query(sparql, graphs)` runs the text with `graphs`
as its default graph and adds nothing, takes nothing. `construct` the same. Every named graph
stays reachable through a `GRAPH` clause, so a text is free to say for itself which graphs it
reads. `query_union` stays for one caller, the sovereign's question about the whole self, and
for a test reading a store back; nothing in the kernel takes it.

**A reader asks by kind and instant, and the store answers with graphs.** `graphs_of(*kinds,
at=None)` is the one lookup: every graph the catalogue types under any of the kinds, this
agent's where the store has been told whose it is, holding at `at` where an instant is given
and whatever its period where none is. No clock is read in it; a reader meaning *now* says so
with the clock it holds. The one thing the lookup knows about a kind is what
`orexis:RecordGraph` means (#645): a record is handed as it stands whatever instant is asked
about, since its period says how long it is worth believing and not when it holds.

**The kinds are kernel terms, and a runner names them.** `PUBLIC`, `BELIEF`, `STATE`,
`PREDICTION`, `RECORD`, `DESIRE`, `WANT`, and two statements of what a rule is answered over:
`KNOWN` — everyone's knowledge, what is, the records, the desires and the wants — and
`FORESEEN`, the same with what is expected at the instant. Genesis names `PUBLIC` for a
derivation's `USING`; the judge names `FORESEEN` at each instant it judges at; the planner
builds one list per node, `KNOWN` at the node's instant with the node's readings in the
state's place; the keeper names `KNOWN` for a precondition; effects names `KNOWN` for an
action's rule unless the search hands it a world. A package puts its graph under a kind to be
read by them — the pick record is a record now — and a kind nobody asks for is nobody's
business. No class hides anything.

**A text that reads one graph names its kinds in SPARQL.** A want lives in one graph, so the
wants collection asks the catalogue itself:

```sparql
GRAPH ?g { ?w a orexis:Want … }
GRAPH ?catalogue { ?catalogue a orexis:CatalogueGraph . ?g a ?kind . VALUES ?kind { … }
                   OPTIONAL { ?g dcterms:temporal ?period … } }
FILTER(!BOUND(?start) || ?start <= ?now) FILTER(!BOUND(?end) || ?end > ?now)
```

and is handed no default graph at all. A pattern that spans graphs — a grant reading
`market:hosts` from the derived graph beside `market:matchesBy` from the world — cannot be
written that way, because a basic graph pattern inside one `GRAPH` block matches within one
graph and SPARQL has no `FROM` by type. Such a text is handed the graphs of the kinds it
names, computed by the same catalogue. Those are the two forms, and nothing else exists.

**Every row carries every kind.** `Store.entry` writes the class a writer names and each
class the vocabulary puts it beneath; genesis transcribes the vocabulary's declared graphs
through `classify` so a world graph's row says `a orexis:PublicGraph` outright; and at open
`close_catalogue` says it again of every row, for a volume or a case that wrote one class. So
a text asks `?g a orexis:WantGraph` and a pursued graph answers, with no path walked across
two graphs — which `tests/test_inference.py` would refuse in any case.

**The desire modality reads by its kinds.** Its projection copies the catalogue and the
vocabulary beside the desires, the wants and the records, and its read surface asks over
`HELD` — stated once, by the modality that owns the store — and stays bound to the copy it
was made over.

# Refused

**The union of all graphs as the default read.** "If you select without specifying a graph,
doesn't it search in all?" It reads the default graph, which is empty here, and pyoxigraph
treats the union as the default only when asked. Asked always, a reader would read every
sibling world of a search, next hour's predicted reading as the present, a lapsed claim and a
closed round until the sweep, and a judgment's rows beside the facts they report on. A reader
need not know where a fact lives — a free `?graph` ranges over every named graph — but it
has to leave those out, and leaving out is what naming a kind is for.

**A default dataset in the store.** `query` could have kept reading public knowledge unless
told otherwise, sparing a hundred call sites a second argument. Refused, because a caller
that did not say what it read was the objection; the sites say it, and the helpers that are
handed a way to ask are handed `store.reader(PUBLIC)`.

**Treatment by subclass.** The five-class rule was tidy and had a reason for each class.
Refused as the thing itself: a store that infers behaviour from a type tree has to know the
tree's shape, and a package told the store how to behave by choosing a superclass.

# Seams left open

- **`orexis:WorkingGraph` and `orexis:PossibleGraph` name no treatment now.** Review's three,
  the judgments and the scopes still sit under the first, the deliberation graph under the
  second, and the store does nothing with either; they are content classes nobody asks for.
  Retiring them is a vocabulary change with its own cases to regenerate.
- **A plain `graphs_of(PUBLIC)` reads a public graph whatever its period.** No shipped world
  states a period on a public graph; a reader that would care says `at`.
- **`effects` and the affordances collection state a default of their own** — `KNOWN` as it
  holds now — for the actuator standing in the present, so that a caller with no world to hand
  in hands nothing. Each is a runner stating its kinds, once, in its own file.
