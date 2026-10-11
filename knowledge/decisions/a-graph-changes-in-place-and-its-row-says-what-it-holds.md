---
type: Decision
title: A graph changes in place, and its row says what it holds by the hash of its content
description: >-
  The sovereign, 2026-10-11, reviewing the versioning record before it was built - why not edit in
  place and keep a version on the graph, as optimistic locking does. Decided - a belief or a
  prediction is changed under its name, and every writer that changes one stamps the hash of what
  it now holds on its catalogue row (orexis:hash), as a ground and a possible world already carry
  theirs; a test holds every belief and prediction standing after every world's tests to hash as
  its row says, so a writer that forgets to stamp fails the build. What changed since a copy was
  made is then the names that came and went and the names whose hash moved. A change to the row
  alone - a period ended, a flag flipped - is metadata and is no change of content. Supersedes
  a-graph-is-never-changed-under-its-name. Refused - a new name per change, keeping superseded
  versions until no pass pins them, a counter on the row, and the written signal alone.
status: accepted
timestamp: 2026-10-11T21:00:00Z
---

# Context

Slice 5 of [#953](https://github.com/ShishkinDmitriy/orexis/issues/953) will refresh the
[imaginarium](/domain/planning/imaginarium.md) by what changed rather than copying every belief again
each pass: copying is up to a fifth of planning, and between two passes the graphs that changed hold
4 to 25 percent of the quads. A refresh that keeps a copy has to know the copy is still right. The
one failure it has to rule out is a copy gone stale with nothing to notice it, which slice 1 already
met once: a changeable piece left standing beside a fresh copy of its source put a disk on two pegs.

[a-graph-is-never-changed-under-its-name](/decisions/a-graph-is-never-changed-under-its-name.md)
answered it by renaming: every change writes a new version under a minted name and forgets the one
before, so a name that stands holds what it held and a refresh diffs names. Reviewing it before the
build, the sovereign asked why a version cannot simply be a property of a graph edited in place.

Read against the code, the renaming carried no guarantee of its own. A writer could still edit a
graph under its name; what caught one was the record's test, the hash each version's row stated at
its minting compared to what it held. That test holds a graph edited in place just as well, and the
renaming cost every reader that finds a graph by the name it derives — an arrival's state, a
statement's belief, a committed step, the executor's own graph — a lookup by identity, and every
writer that forgets and rewrites a name a counter. Nothing reads a superseded version, so the old one
was forgotten at once; keeping it bought nothing either.

# The decision

**A belief or a prediction is changed under its name, and its row says what it holds.** Every writer
that writes, adds to or takes from such a graph stamps the hash of its content on the graph's catalogue
row as it finishes, `orexis:hash`, through `hash_named_graph`: the hash a ground and a possible world
already carry, canonical over blank nodes and rounded on numbers, and replaced rather than added to.
The writer knows which graphs it changed, so it hashes those alone. That is every writer of the agent's
beliefs and predictions: the boot and its documents, a transition's state and what it deletes from,
an inference's revisions, what is extracted of a statement, a silence, a forecast, a committed step, a
fictive step's write, and a prediction's stretches.

**It is held by a test, not by care.** After every world's tests, every belief and prediction standing
in each store they made hashes as its row says. A writer that changes a graph and does not stamp it, or
writes one with no stamp at all, fails the build — which is what the renaming promised and could not
deliver alone.

**What changed since a copy was made is the catalogue's to say**: the names that came, the names that
went, and the names whose hash moved. A copy keeps the hash it was made with, and a refresh copies a
name again only where the row's hash is not the copy's. A name forgotten and written again — a
prediction's stretch, a forecast, a statement said again — needs no rule of its own: its hash moved if
its content did, and its copy stays right if it did not.

**The row is metadata.** A period ended, a committed step's window closed, revision's `settled` flag
flipped: each changes the row and not the content, is no change of what the graph holds, and stamps
nothing. A refresh reads the rows of the names that stand as it reads the hash, since the catalogue
crosses whole.

# Why

**The guarantee is the test.** Renaming and stamping both rest on a writer doing its part, and both are
held to it by one comparison of what a graph holds against what its row says. Of the two, stamping
asks the writer one line and asks no reader anything.

**A hash and not a counter.** A counter on the row is optimistic locking's version, and a writer that
forgets to bump it leaves a number nothing can check, since the number says nothing of the content. A
hash says what the graph holds, so a forgotten stamp is a mismatch a test can see. The locking half of
optimistic locking — refusing a writer whose read went stale — has no work here: one thread runs every
part, so no two writers meet.

**Nothing reads the past of a belief.** The series holds what was believed when; the belief base holds
what is believed now, and a graph's name stands for it.

# What was refused

- **A new name per change** ([a-graph-is-never-changed-under-its-name](/decisions/a-graph-is-never-changed-under-its-name.md)):
  every change copies the graph under a minted name and forgets the one before. It guarantees nothing
  the hash on the row does not, and every reader that finds a graph by a name it derives would ask by
  `dcterms:isVersionOf` instead.
- **Keeping superseded versions until no pass pins them**, collected after: what a store does where a
  reader runs beside a writer and must see one moment's content. A pass here is one job on the one
  thread, and it copies what it reads into an imaginarium before it searches, so no writer lands
  inside it and nothing would ever be pinned.
- **A counter on the row**, bumped by each writer: a stamp nothing can check.
- **The written signal alone**: every writer already says what it wrote, and the refresh could copy
  what was said. Right only while every writer says it, and a writer that forgets leaves a stale copy
  that nothing finds; the hash makes the same omission a failing test.

# Seams left open

- **A pass beside a writer.** The day planning runs on a thread of its own, a copy can be made while a
  writer changes its source, and keeping each version until no pass reads it, collected after, is what
  answers it. **The trigger: the first part that runs off the pass's thread.**
- **The agent's own records.** The intentions graph, a want's state and the catalogue are written in
  place by the one package that owns each, and are no belief a copy is made of; they carry no stamp.
  **The trigger: a copy of one made outside its owner.**

# How it is built

[#961](https://github.com/ShishkinDmitriy/orexis/issues/961): every writer of a belief or a prediction
stamps what it changed, and the test holds every world's tests to it. Slice 5 of #953 then diffs names
and hashes.
