---
type: Decision
title: The state is what a scope can change, and everything an agent knows is belief
description: >-
  The sovereign, 2026-10-11 - public, state and belief graphs look alike, and only belief should be a
  kind. Decided - the state is not declared by a graph's kind but extracted, per scope, from
  everything believed - every triple some effect, transition or drift of the scope can write - so
  adding an action makes more of what is known state, as it should; and the public axis goes, since
  who shares a document is how it arrived, which a graph class may not say. orexis:StateGraph and
  orexis:PublicGraph fold into orexis:BeliefGraph. What the two kinds did besides is said by
  provenance, already on every catalogue row - a transition deletes from the agent's own derived
  graphs, revision reads a source beside everything not received, and what defines what the agent
  can do and how it reasons is read only as asserted, so a peer's word is believed as what it said
  and can redefine nothing. Refused - a kind declared per document for what changes, a list of
  exclusions per reader, and a peer gate that admits only triples some scope can write.
status: accepted
timestamp: 2026-10-11T09:00:00Z
---

# Context

Three kernel kinds sort what an agent knows, and to the sovereign they looked like one:

- **`orexis:BeliefGraph`**: what the mind may read as true. Every reader of the mind names it, so
  an observation, a prediction or a possible world is not beneath it and reaches none of them
  ([an-observation-is-a-percept-and-the-mind-reads-only-beliefs](/decisions/an-observation-is-a-percept-and-the-mind-reads-only-beliefs.md)).
- **`orexis:StateGraph`**, beneath it: the part a plan can change. A ground speaks for it
  (`agent/planning/world_at.py`), a possible world forks it, an effect and a transition rewrite it,
  a prediction supersedes it, a peer may say it (`agent/speech/heard.py`) and the executor checks a
  landing against it. The world authors it per document (`<> a orexis:StateGraph` in every
  `state.ttl`), and a domain subclasses it (the market's calls, rounds, bids, claims, presentations).
- **`orexis:PublicGraph`**, on another axis: what every agent of a world reads. The ontology, the
  world, the society, the actions, the drifts, the shapes and the constraints; a query's default,
  what revision reads a source beside, and what a footprint and a scope are read over
  ([who-put-the-fact-there](/decisions/who-put-the-fact-there.md),
  [a-reader-states-the-kinds-it-reads](/decisions/a-reader-states-the-kinds-it-reads.md)).

Two of them answer a question the documents cannot. **What can change is relative to the actions.**
A triple no action writes is fixed; add an action that writes it and it is state, though no document
changed. A kind authored on a document cannot follow that, and the [scopes](/domain/planning/scope.md)
already compute the answer: a scope is a predicate on a key, read off what its actions write
([a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md)), and
`prepare_ground` already leaves behind the state graphs whose members are another scope's alone. It
stops at whole graphs because the kind told it which graphs to look at.

**And who shares a document is how it arrived.** The world's documents are mounted into every agent
of the world; that is deployment. Once loaded they are what the agent knows, beside what it derived
and what it was told, and "a graph class is named for the rows it holds, may not say how a graph
arrived". The catalogue already says how each one arrived: `orexis:Asserted` (the sovereign's
documents), `orexis:Derived`, `orexis:Received`, `orexis:Recorded`.

# The decision

**Everything an agent knows is belief, and `orexis:BeliefGraph` is the one kind of it.**
`orexis:StateGraph` and `orexis:PublicGraph` fold into it. The kinds beneath it stay, each named for
the rows it holds: ontology, world, society, actions, drifts, shapes, constraints, self, forecast,
committed step, the market's calls, rounds, bids, claims and presentations, and the graph a
transition writes. The other modalities stay what they are: desire, want, prediction, possible
world, plan, record, intention, observation.

**The state is extracted per scope, from everything believed.** A scope's state is every believed
triple that some writer in the scope can write:

- each effect of the scope's actions;
- each transition, since a ground runs the transitions a predicted observation triggers;
- each drift, since a prediction writes a predicted observation.

The writers' templates are read once, at boot as the scopes are, with each template's variables
standing for any term and a predicate variable bounded by its own `VALUES`, as a scope already reads
them. They make one query per scope. What it answers is what a ground speaks for, what a possible
world forks and what a prediction supersedes; every other belief is read beside every world as it
stands. A world is then the size of what its scope can change, which is the measured property the
scopes were built for, kept.

**What the two kinds did besides is said by provenance, read off the catalogue:**

- **A transition deletes from the agent's own derived graphs**: owned by the self, arrived
  `orexis:Derived`, and no inference revision (`belief:RevisionGraph`). It never touches testimony,
  an asserted document or what an inference concluded.
- **Revision reads a source beside everything believed that did not arrive `orexis:Received`.**
  The hazard the public-only rule closed was one testimony taking another's side, and that is what
  this excludes; the world's documents, the agent's own state and what was derived stand beside it.
- **What defines what the agent can do and how it reasons is read only as asserted.** The
  ontology, the actions, the drifts, the rules, the shapes, the constraints, the desires and the self
  are read from graphs that arrived `orexis:Asserted`, or were derived from one (the closure). **A
  peer's document is believed as what it said**, a first-order belief about what the peer said, and
  can redefine nothing, since no reader of actions or rules takes a graph that arrived
  `orexis:Received`. *Amended 2026-10-11: a peer's word becomes testimony instead, in a kind no reader of
  the mind is handed, and only the agent's rules make it a belief
  ([a-peers-word-is-testimony-and-a-rule-makes-it-a-belief](/decisions/a-peers-word-is-testimony-and-a-rule-makes-it-a-belief.md));
  until that is built the gate stays at the writer, `heard`, and no reader keeps it.* This is the gate speech kept by admitting only kinds beneath
  `orexis:StateGraph`; it moves from the writer to the readers, which is where "a reader states the
  kinds it reads" already put every other choice.
- **The executor checks a landing against the present beliefs.** A step's prediction names its
  triples (`execution:adds`, `execution:retracts`), so nothing about kinds is needed to compare.
- **A query's default is the beliefs**: `graphs_of(BELIEF)`, which the public list was a part of.

# Why

**Only the actions say what can change.** A kind on a document is a guess about the actions made
by whoever wrote the document, and it goes stale the day an action is added. The scope already
derives the answer from the actions; this extends the derivation from "which graphs" to "which
triples", where it was always going to have to be read.

**One axis per question.** Belief versus the other modalities is what the mind may take as true.
Whether a triple can change is a question about the scope's writers. Who wrote a graph and whether
to trust it is provenance. Three kinds answered three questions and looked alike because two of
them were answering the second and third questions with a class.

**Provenance is already there.** Every catalogue row carries `orexis:arrivedBy` and
`orexis:beliefsOf`. The boot already finds the world's shared documents by provenance, not by kind
(what arrived asserted and nobody owns, `agent/runtime.py`).

# What was refused

- **A kind declared per document for what changes**, today's `orexis:StateGraph`. Authored by
  whoever writes a world, and right only while the actions stay as they were when it was written.
- **A list of exclusions per reader**: one `orexis:BeliefGraph` and each reader leaving out the
  self, the ontology, forecasts and committed steps by name. A kind said by absence is a kind two
  readers disagree about; the per-scope query says it once, from the writers.
- **Forking every belief into every world.** The ontology and the world graph copied into each
  ground, and an effect able to rewrite the self graph. It throws away the scopes' measured result
  that a world is about one percent of the present.
- **A peer gate admitting only triples some scope of the agent can write.** It sounds like the
  same idea applied to speech, but it refuses the market: a host's actions issue claims and write no
  bid, so every bid a bidder sends would be refused. What a peer may change in the agent's beliefs is
  not what the agent can change; the safety needed is only that a peer cannot redefine the agent,
  which the asserted-only readers give.

# Seams left open

- **A triple two scopes can write is state in both**, read twice and forked in each. Today's
  graph-grained rule has the same property.
- **A belief no scope can change is never forked**, even where a want reads it; it is read beside
  each world. That is correct while nothing changes it, and is what "what a fork may skip is bounded
  by what a rule may read" asks of the reading, not the forking.
- **The world's documents still arrive as files mounted per world**, and onboarding still decides
  which documents each agent loads ([a-documents-kind-says-who-reads-it](/decisions/a-documents-kind-says-who-reads-it.md)).
  Only the kind that said "shared" goes; the sharing is deployment.

# How it is built

> **The first slice, built 2026-10-11 (#953).** The cut is made in `lay_ground`, not where the
> imaginarium is filled, because a case lays its grounds in its own store; a refresh takes it back with
> the graph it was cut from ([changeable](/domain/planning/changeable.md)). The drifts' share is the
> predictions': a prediction writes what it adds, and its retraction takes out of a ground what stands
> there. What another scope alone can change is still dropped whole, by graph, as `_of_another_scope`
> did: a pattern of a predicate cannot tell one bed's soil from another's, so the three classes a scope
> sees — changeable by it, by others alone, by none — wait on a key for the second. Measured on the
> allotment, alternated in one session: 9.6 s against 8.9 s for one test, the difference each template's
> one parse, remembered after.

> **`orexis:StateGraph` folded, built 2026-10-11 (#953).** The kernel declares no state kind, and the
> worlds' `state.ttl` documents and the market's five kinds are beneath `orexis:BeliefGraph`. What the
> kind did is said as follows. **The agent's own state** — what a transition reads beside its arrival
> and deletes from, and what a ground's transitions carry — is every belief the agent derived that is
> no revision and nothing everyone reads; it stays one graph per arrival, so a silence still ends a
> state by its graph's period, and the belief base keeps the two CONSTRUCTs while planning takes the
> engine's update. **The present** a landing is checked against, refine's frame and the present ground
> read where it lies are every belief, and the walk is woken by a belief revised that is no committed
> step. **A fictive step** takes its retractions out of every belief of the agent's holding them and
> puts its additions where they stood, so a drive's new cell lands beside the disks the tower's rules
> read it with; one replacing nothing goes into the executor's own. **The speech gate stays at the
> writer** as an interim, a kind beneath belief and not beneath public, until a peer's word is
> testimony ([a-peers-word-is-testimony-and-a-rule-makes-it-a-belief](/decisions/a-peers-word-is-testimony-and-a-rule-makes-it-a-belief.md),
> #958); a peer may then say a committed step or a forecast, kinds the state kind kept out, as it could
> always say a subject belief. A revision of a belief is a belief, so the readers that walk the agent's
> own leave revisions to go with their sources. Every case reads as it did.
> *#958 built it: a peer's word is a statement, the interim gate is gone, and slice 4 moves no gate.*

> **Amended 2026-10-11: what changed is a diff of names.** A graph a copy is made of is never changed
> under its name ([a-graph-is-never-changed-under-its-name](/decisions/a-graph-is-never-changed-under-its-name.md)),
> so the imaginarium refreshes the names that came and went and keeps every copy of a name that stands,
> hearing no signal from any writer.

After #951, since the writers' templates are what define the state and #951 makes each writer one
update text parsed by rdflib. Then three slices, each keeping every world's figures:

1. **Extract the state per scope** and make the ground speak for it, with `orexis:StateGraph` still
   declared, until every planning snapshot reads as before.
2. **Fold `orexis:StateGraph` into `orexis:BeliefGraph`**: the transition's target, its delete scope
   and the speech gate move to provenance; the worlds' `state.ttl` documents and the market's kinds
   are beneath belief.
3. **Fold `orexis:PublicGraph`**: the query default, revision's neighbours and the footprints read
   the beliefs. #913 found a footprint misread once a pattern only the agent's own store binds was
   read; that is re-measured here.

Once built, this supersedes in part
[who-put-the-fact-there](/decisions/who-put-the-fact-there.md) (the public class),
[a-reader-states-the-kinds-it-reads](/decisions/a-reader-states-the-kinds-it-reads.md) (the public
default), [a-transition-changes-the-state-and-an-inference-only-concludes](/decisions/a-transition-changes-the-state-and-an-inference-only-concludes.md)
(the target and the delete scope), and the modality page's state row — both reconciled when the kind
folded.
