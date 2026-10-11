---
type: Decision
title: A graph is never changed under its name; a change makes a new version, and the one before is forgotten
description: >-
  The sovereign, 2026-10-11 - instead of deleting from a graph in place, make a new graph that
  supersedes the one it retracts from, copying it with the change applied. Decided - the content of a
  graph a copy is made of, a belief or a prediction, is fixed for as long as its name stands, and a
  name forgotten is never written again. A writer that would put a triple into one that stands, or take
  one out, makes a new version under a new name, the old content less what goes and plus what comes,
  carrying the graph's lasting identity (dcterms:isVersionOf, the name its first version had), and the
  version before is forgotten as it is written. Nothing tracks an outdated version - nothing reads one,
  and history is the series'. What changed since any moment is then which names came and went in the
  catalogue, and a copy made of a name can never go stale. Refused - changing a graph in place, keeping
  every version in the belief base, a link from each version back to the one it replaced, a log of
  changes beside mutable graphs, and a stamp each writer updates on the graph's row.
status: accepted
timestamp: 2026-10-11T18:00:00Z
---

# Context

Every belief graph is changed in place today. A transition deletes the state before from whichever of
the agent's derived beliefs holds it (`agent/belief/trigger.py`); a fictive step takes its retractions
out of the beliefs that hold them and puts its additions where they stood (`agent/execution/executor.py`,
#960); a peer saying a document again replaces its graphs under the same names (`heard`, `said`); and
the state graph of an arrival is written into again by a later arrival of the same name. The name stays
and the content under it moves.

Three things have each paid for that:

- **A copy cannot know it is stale.** The imaginarium copies graphs by name each pass. Slice 1 of #953
  left a changeable piece of a graph standing beside a fresh copy of its source, and a disk stood on two
  pegs. Slice 5 would refresh only the graphs that changed, and to know which it must hear every writer
  say what it wrote; a writer that forgets leaves a stale copy, found by nothing.
- **A reader cannot tell what a change did.** What a graph held before a write is gone, so the one way
  to see a change is to have been watching, which is what the runtime's `written` signal does by the
  graph and nothing does by the triple.
- **Where an addition goes is a choice per writer.** The fictive write had to choose, and its first
  choice (into the executor's own graph) left a drive's new cell apart from the disks the tower's rules
  read it with (#960). Versioned, the addition goes into the new version of the graph the retraction
  came out of, which is the choice #960 made, said once for every writer.

The imaginarium never had the problem. A step forks its world into a child and leaves the parent as it
was, so a possible world is never changed under its name, and what a step changed is the diff of two
graphs that both still stand ([a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)).
The sovereign asked for the belief base to work the same way.

# The decision

**The content of a graph a copy is made of is fixed for as long as its name stands.** That is every
belief and every prediction: what the imaginarium copies and what a reader of the present is handed. A
writer that would put a triple into such a graph that already stands, or take one out of it, instead
makes a new version of it:

- **The new version** is the old content less what is taken out and plus what is put in, under a new
  name, minted from the store's counter as a possible world is. Its catalogue row carries the old one's
  kinds, owner and period, `orexis:arrivedBy orexis:Derived`, and `dcterms:isVersionOf` the graph's
  lasting identity, the name its first version had.
- **The version before is forgotten** as its successor is written, with its revisions and its row. It
  is not ended and kept, and nothing links back to it: nothing reads an outdated version, and what was
  believed before is the series' to keep
  ([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)).
- **Adding is a change too.** A copy made of a name lacks what is added under it later as surely as it
  keeps what is taken out, so a refresh that trusted the name would miss either. A graph written once
  and never again — a percept, a prediction, a committed step — makes no version, and those are most of
  what is written. A graph that would be left empty is not versioned; it is forgotten.
- **A name forgotten is never written again.** Prediction forgets a key's stretches and writes the new
  ones under the names it used before (`agent/prediction/predict.py`), so a name a copy holds would hold
  other content; each is minted afresh, as a possible world's is.
- **A graph's lasting identity is the name its first version had**, an IRI that stands on every
  version's row though no graph of that name is held after the first change. A reader that asks for a particular graph
  rather than a kind of graph — `heard` replacing what a peer said under a name, `trigger` writing again
  into an arrival's state graph, the executor finding its own — asks for the version whose
  `dcterms:isVersionOf` is that name, or the name itself where it was never versioned.

**What changed is a diff of the catalogue.** Between two moments, the graphs that changed are the names
that came and went; a name present at both holds exactly what it held. Slice 5's refresh
copies the new names and forgets the gone ones, and hears no signal to do it.

**It is held by a test, not by care.** Each such graph's row states the hash its content had when its
name was minted, and a test asks, after every world's tests, that every belief and prediction standing
still hashes as it did, and that no name was minted twice. A writer that puts into or takes out of a graph in place fails it.

# Why

**One mechanism for the imaginarium and the belief base.** A step forks a world rather than editing it;
a change forks a belief rather than editing it. The diff of two graphs is how a step's prediction is
read, and it is how a belief's change is read.

**A name that cannot go stale makes every copy safe.** A copy keyed by name is correct for as long as
the name stands, so nothing has to tell the imaginarium what to recopy, and no writer can forget to.

**What nothing reads is not kept.** Sensing forgets a percept past the depth its rules read; the
executor forgets a committed step once its window has ended; a term nobody reads is annotation. An
outdated version is read by nothing — not the search, not a reader of the present, not slice 5's diff,
which needs only the names standing — so it is forgotten, and the one thing every version carries is
what three readers do ask: which graph it is.

# What was refused

- **Changing a graph in place**, today's. A name stands for different content at different moments, so
  a copy goes stale silently, a change cannot be read after it is made, and every writer chooses where
  its addition lands.
- **Keeping every version in the belief base**: an ended version kept until something forgets it, so a
  reader could stand at a past instant and be handed what was believed then. Nothing reads the past of a
  belief; the series already holds it, and the belief base would grow with every reading. Kept, the
  versions are the garbage the sovereign named.
- **A link from each version back to the one it replaced**, `prov:wasRevisionOf`, as first drafted:
  the version it names is forgotten in the same act, so the link points at a name with no row and no
  content, and nothing follows it. Provenance that nothing reads is annotation, and the history it
  would trace is the series'.
- **A log of changes beside mutable graphs**: each change also written as a graph of what went and what
  came. Two records of one change, the graph and its log, which must agree; and a copy still goes stale
  until the log is replayed into it.
- **A stamp each writer updates on the graph's row**, a version number or a hash rewritten with every
  write, read by the refresh to see what changed. The cheapest, and it is the `written` signal again in
  another place: right only while every writer remembers to update it, and a writer that forgets leaves
  a stamp that lies.

# Seams left open

- **What the agent's own records keep doing in place.** The intentions graph, a want's state and the
  catalogue itself are written in place, each by the one package that owns it and reads it back. They are
  no belief a copy is made of for a search, and nothing else reads them. **The trigger: a reader of one
  of them that is not its owner, or a copy of one made outside its owner.**
- **How deep a chain is kept.** None past the present, today. A rule that reads a belief's past — a
  state held for an hour, a count of changes — would keep as many as it reads, as sensing keeps a
  sensor's percepts as deep as stuck's rule reads them, and with them a link back from each version to
  the one it replaced, which something would then follow. **The trigger: the first such rule.**

# How it is built

[#961](https://github.com/ShishkinDmitriy/orexis/issues/961) holds the build, before slice 5 of #953. The store's one act that versions a graph first, with
its row and its forgetting; then every writer that changes a belief or a prediction moves to it — a
transition's deletions, a fictive step, `heard` and `said` saying a graph again, an arrival's state graph
written into again, and prediction's stretches rewritten — and every reader that asks for a particular graph asks by `dcterms:isVersionOf`; then the
hash on the row and the test that holds every world's beliefs to it. Slice 5 is then the catalogue's
diff.

This amends [the-state-is-what-a-scope-can-change-and-everything-known-is-belief](/decisions/the-state-is-what-a-scope-can-change-and-everything-known-is-belief.md)
in how slice 5 learns what changed, and, once built, the transition and speech pages where they say a
deletion is taken out of a graph in place.
