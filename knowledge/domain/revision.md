---
type: Domain Concept
title: Revision
term: http://example.org/orexis/belief#RevisionGraph
description: >-
  A belief derived from beliefs by a rule — what the rules the store holds conclude of a graph,
  written into a graph of the source's own, derived from it, never deleting. The rules are SHACL
  1.2 Inference Rules' adopted as they stand: a rules graph, a package's rule set, SPARQL rules
  by layer and order. Concluded on the present only, never in a search.
---

# What it is

A **revision** is a belief derived from beliefs: *this reading is Below*, *this pot is dry*,
*this observation is a kind of sample*, concluded by a rule from what a graph says beside what
stands. The rules are SHACL 1.2 Inference Rules' and nothing of ours is added: a graph in the
role of a rules graph is typed `sh:RulesGraph`; a package ships its rules as a `sh:RuleSet`,
an IRI with `sh:hasRule` and `sh:includesRuleSet`; a rule is a `sh:SPARQLRule` with one
`sh:construct`, placed by `sh:layer` and `sh:order`, taken out by `sh:deactivated`, run once
by `sh:runOnce`. An [action](/domain/action.md) carries a construct too and is no rule: an
[effect](/domain/effect.md) is applied once, by a search, to the world a step leaves.

`revise` (`agent/belief/revise.py`) runs a rules graph's **default rule set**, every global rule
in it — one not linked to a shape by `sh:rule`, since a shape rule runs per focus node and
nothing here has one — layer by layer over an **evaluation graph**: what the caller hands as
standing beside the source, the source itself, and what has been concluded of it so far.
Within a layer one iteration runs the run-once rules first, then the iterating rules are run
again while an iteration concludes something new; within an iteration the rules run in order,
and rules of one order see none of each other's inferences until they have all run. What is
inferred is what the base graph does not already hold. All of that is section 8 of the draft,
within a **budget** of rule executions, the unit revision spends, which the
[deliberator](/domain/deliberator.md) states per pass. A source the budget cuts short keeps what was concluded, its row saying the rules
did not settle, and the next pass continues it; a rule minting new content every iteration,
the draft's own worry and the reason `sh:runOnce` exists, spends the budget and is said in the
log every pass rather than looped on. Where the draft says a rule set fails, a rule of a type this
engine cannot execute, a shape rule, or a construct that will not run, this engine reports an
error naming the rule and runs the rest, since a package's bug must not take an agent down.
`sh:condition`, `sh:expectedPredicate`, temporary triples and `sh:sourceRule` are in the draft
and not run here.

# It is concluded and never deleted

A rule states what it adds and nothing about what it removes — the draft has no deletion, and
neither does this. The revisions of a graph live in **a graph of the source's own**
(`belief:RevisionGraph`, the draft's inference graph, which it names as a role and not a
class), `prov:wasDerivedFrom` the source, the source's owner's, holding for the source's
period. So a revision is a function of its premises: two graphs stating the same facts conclude
the same, a possible world is hashed by its own facts and never by these, and *replacing* a
revision is the source being rewritten and concluded over again. Nothing in the rules ever
names what it takes away.

A revision already concluded is not written twice, and **a blank node is its content**: a
construct that mints one mints a fresh label every iteration, and by label no fixpoint would
come; by content the second iteration's node says what the first's said, and stands once. The
draft's answer to the same problem is `sh:runOnce`, honoured too.

# Where it runs: on the present, and nowhere else

A rule runs over a reading when it is written and over a prediction when it is predicted. It
never runs in a search: planning speaks the derived vocabulary, a precondition reads *the
reading is Below* and an [effect](/domain/effect.md) writes *the reading is Inside* itself, so no
fork and no ground is revised. Execution then holds a step to the present, and the present
reaches *Inside* when the next reading arrives and a rule concludes it from the number; the wait
is the bridge between the instrument's vocabulary and the mind's, and it is where the wait
belongs. A graph with no catalogue row is invisible to every reader by kind, so a writer that
means its graph never to be seen without its revisions writes the graph, revises it and
classifies it last; that is the whole of the discipline, and it is a convention rather than a
concept.

# What a plan may change is what the actions say, not a graph

The direction settled for the final state, not built yet: each action's footprint — derived from
its [effect](/domain/effect.md)'s construct and retraction, never authored — is one query whose
result is the facts that action can mutate, and a possible world is the union of every action's
result over everything holding at the instant, whatever graph each triple sits in: a reading, a
revision drawn from it, a prediction whose window has opened. Everything else is context, read
beside the world. A graph kind then says who wrote a graph, whose it is and when it holds, and
never what a plan may change; so a revision an action can write reaches the ground and the
executor because an action writes it, and no revision graph has to be typed as anything for
that. The retraction's pattern is what gives a keyed node its whole shape in the world, and the
same footprints partition the scopes, one analysis with two readers.

# What it is not

It is not a gate. A validation stood beside it for a day — every new graph held to the
packages' shapes, a violation forgetting it whole — and a proposal state to serve it, and both
were struck: belief revision keeps the new information, dropping testimony over a shape is a
gate wearing revision's name, and a law's objection to a graph is a revision a rule can
conclude, which the mind may then want to repair. Any belief is accepted, and revised, and
nothing stands between a writer and the store.

This structure — rules stored as triples, run over an evaluation graph the caller hands, their
result landing in a graph of its own — is the one an effect and a
[prediction](/domain/prediction.md) are to converge on, and the three differ only in when they
run, where the result lands and whether they replace standing facts. Only revisions are built to
it so far.

# The word

*Revision* is also review's word in 0.1.0, for the re-pick of a belief within its mandate; that
is its own concept and keeps the word, as a rule's premises and a capability's premise do. This
page is the belief revision function's product, and the two do not meet.

# Related

- [belief-base](/domain/belief-base.md) — where the source and its revisions live.
- [inference](/domain/inference.md) — the 0.1.0 materialisation of what the vocabulary entails,
  which a rule over public knowledge would replace.
