---
type: Decision
title: A graph class is named for what it holds
description: >-
  Asked what the roots graph is and whether its class should say desire, and what the pick
  record is. A graph class names the KIND of row a graph carries, as a repository is the
  plural of what it holds - `orexis:DesireGraph` for graphs of desire rows (the roots, the
  promises), `orexis:WantGraph` for graphs of want rows (each pursued want), and the world's
  asserted graph under both, since one world ratifies a desire and three ratify a want.
  Three things were refused - naming a class for the derivation's role in the rows, a fresh
  spelling to keep clear of the retired modality class, and a want name for the asserted
  graph - and the pick record's name for eyes says picks, moved once at boot for a volume
  that still says beliefs.
status: accepted
timestamp: 2026-09-19T12:00:00Z
---

# The question

Asked by the sovereign after #708 made every graph's name a convention for eyes: what is
`orexis:RootsGraph`, and should it be `orexis:DesireGraph`? And what is
`orexis:PickRecordGraph`? The first holds one agent's `orexis:Desire` rows with their
met-tests, declared at birth from the ranges the world states and endowed on amendment. The
second holds the record of picking — the [pick](/domain/pick.md) per term that birth authored
and [review](/domain/review.md) re-picks — and is still called `beliefs/<agent>` for eyes,
the misnomer the vocabulary's own comment on `orexis:BeliefGraph` records.

# The rule

**A graph class is named for the kind of row the graph holds**, as
[a-repository-is-named-for-what-it-holds](/decisions/a-repository-is-named-for-what-it-holds.md)
names a collection for the plural of its element. A reader asks by class
([who-put-the-fact-there](/decisions/who-put-the-fact-there.md), amended by #708), so the
class is what a reader means, and a reader means *the graphs of desires* or *the graphs of
wants* — never *the roots*, which is what those rows are TO THE DERIVATION. Two content classes in
`agent/ontology.ttl`:

- `orexis:DesireGraph` — a graph of `orexis:Desire` rows. The roots graph is one, and
  `progression:PromisesGraph` is beneath it, since a promise the bridge raises is written as
  a desire the agent holds.
- `orexis:WantGraph` — a graph of `orexis:Want` rows: one graph per want the derivation
  minted, and the world's asserted graph where a world ratifies a want directly. WHICH of the
  two is the arrival axis, `orexis:arrivedBy`, and never a subclass — see below.

The planner's want graphs and the desire projection ask for both and for the obligations
record, and nothing names a role. A want is not a desire (`orexis:Want` says so, measured in
#681), so neither content class is beneath the other.

# What was refused

**A class named for the role.** `RootsGraph` said what the rows are to the derivation — a root is
what a want is derived under — and the rows were `orexis:Desire` all along. Two names for one
kind of row in the T-Box is the synonym the dictionary refuses between pages: a reader meets
both, looks for the difference, and the meanings drift. The derivation keeps the word *root* in its
prose, as the role a desire plays there, and the graph's name for eyes stays `roots/<agent>`.

**A fresh spelling.** `orexis:DesireGraph` had existed and was retired by #312
([a-store-is-a-modality](/decisions/a-store-is-a-modality.md)) as a MODALITY class, saying
which store a graph belonged to; a spelling such as `DesiresGraph` would have kept clear of
it. Refused: the retired claim and this one are different claims — what store, against what
rows — and a second spelling for *a graph of desires* would be the same synonym one level up.
The record is amended to say the spelling returned with a content meaning, and the five pages
that cited the retired example now read a true one.

**A want name for the asserted graph.** `orexis:AssertedDesireGraph`, declared in #708, held
what a world ratifies directly of what its agents want: a standing `orexis:Want` in the
courier, hanoi and the tower, an `orexis:Desire` in the greenhouse. No content word fits four
worlds, so it sat beneath both content classes and kept the name of the modality that projects
it.

**Both names were wrong, and the rule that says so is the one above the classes.** A named
graph is classified on three independent axes — what its content asserts, whose it is, and how
it ARRIVED — and a content class may not encode the third. `AssertedDesireGraph` said its
arrival in its name; `deliberation:PursuedGraph` said nothing else at all, since its whole
content beyond `orexis:WantGraph` was that the derivation rather than a world wrote the rows.
Both are retired, and each graph carries a content class per kind it holds plus
`orexis:arrivedBy`.

What the conflation cost was not tidiness. With the derivation's wants under a class of their
own and a world's under another, no read could ask for *a graph of wants* and mean both — so
the kernel read its own and judged the world's a SECOND time, at read time, in the collection
that assembled what the agent was considering. Taking the arrival off the content axis is what
let one judging pass answer for every want.

# The pick record's name

`orexis:PickRecordGraph` was named correctly by this rule already; its name for eyes was not.
The helper spells `picks/<agent>` now, the rule token that names it is `$picks`, and a volume
written under `beliefs/<agent>` is moved once at boot, before birth asks whether the agent
exists — since birth reads the pick record's presence as the answer, and a rename that left the
old name in place would have re-authored every pick on the next start.

# Seams left open

- **The world's files still say `beliefs/<agent>.ttl`.** They are the sovereign's authoring
  surface and the runbooks teach them by that name; the file holds the first picks, and its
  name is the world's to change.
- **`orexis:beliefsOf` and `Beliefs.graph` keep their names.** The property says whose a
  graph is, of every kind; the attribute is the belief base's own record graph, whatever it
  holds.
