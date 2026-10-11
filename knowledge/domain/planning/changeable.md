---
type: Domain Concept
title: Changeable
term: http://example.org/orexis/planning#ChangeableGraph
description: >-
  What a search can change of a belief graph - every triple a writer of its scope can write - cut
  out of the graph into a changeable graph of its own as the grounds are laid. A ground holds the
  changeable graphs and nothing else, so a fork copies only what a step can change, and a world
  reads what is left of every graph beside it. The two parts never share a triple.
---

# What it is

```turtle
# before the grounds are laid: one state graph, the van's cell beside the parcel's destination
GRAPH :state { :van courier:at :c0_0 . :parcel courier:destination :c1_1 . }

# after: the cell the Drive writes is changeable, the destination stays where it was
GRAPH :state            { :parcel courier:destination :c1_1 . }
GRAPH :state.changeable { :van courier:at :c0_0 . }
```

A belief, public or record graph a search reads is cut in two in the
[imaginarium](/domain/planning/imaginarium.md), as `lay_ground` lays the grounds: the triples some
writer of the search's [scope](/domain/planning/scope.md) can write go into a `planning:ChangeableGraph`
derived from the graph (`prov:wasDerivedFrom`), and the graph keeps the rest. The present ground is laid
from the changeable graphs, a [possible world](/domain/planning/plan.md) is forked from a ground, and
`world_at` reads every remainder beside the world. The belief base is never cut: the split exists for
a search, and is made again each pass, the last pass's cut taken back first.

# Who the writers are

What can change is said by what writes, never by a document's kind
([the-state-is-what-a-scope-can-change-and-everything-known-is-belief](/decisions/the-state-is-what-a-scope-can-change-and-everything-known-is-belief.md)):

- **an [effect](/domain/planning/effect.md)** of one of the scope's actions, applied in a fork;
- **a [transition](/domain/belief/transition.md)**, which a predicted observation triggers in a ground;
- **a prediction**, whose retraction takes out of a ground what stands where it adds.

Each template of an effect or a transition is a pattern: an IRI or a literal it states is fixed, a
token, a variable or a blank node is anything, and the subject always is. A predicate variable is the
IRIs its own `VALUES` bounds it to. A prediction is a pattern per predicate it adds, a type with its
class. A writer whose templates cannot be read makes every triple changeable.

# Why a pattern may match too much and never too little

Too much costs a fork a few quads: a triple no step ever changes is copied anyway. Too little breaks a
world: a triple a step writes that no pattern caught is written into the fork while the old one stays
in the remainder, read beside it, and a shape holding over every value sees both.

What defines what the agent can do is never cut: the vocabulary, the actions, the drifts, the shapes,
the constraints and the derivations are no fact a step changes.
