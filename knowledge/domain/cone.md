---
type: Domain Concept
title: Cone
description: >-
  The tree of possible worlds a pass builds under the present for one want — each node its
  parent plus a diff, beside the frontier not yet expanded and the facts every diff was
  measured from. It outlives the pass that built it: the next pass re-roots it where the
  present turns out to be one of its worlds, and abandons it whole where the invariant half
  moved. One want, one cone; the graphs its nodes name are held elsewhere.
---

# What it is

A pass of the [planner](/domain/planner.md) leaves a TREE behind rather than a single line of
reasoning. Its root is where the agent stands; every other node is a world some
[step](/domain/step.md) would reach; an edge is that step's [effect](/domain/effect.md). The
cone is that tree together with what searching it further requires — which worlds have been
reached already, which are still worth opening, and the base the diffs were measured from.

The name says the shape: what may happen widens away from where you stand. See
[the-future-is-a-cone-and-the-present-is-identified-in-it](/decisions/the-future-is-a-cone-and-the-present-is-identified-in-it.md).

# What it holds

- **Nodes**, each carrying its diff against the base, what it would cost, how urgent the want
  remains there, and the ground it was predicted on.
- **The frontier** — nodes reached but not opened, which is what lets a later pass carry on
  where the budget ran out rather than beginning again.
- **An index of worlds already reached**, so a path that doubles back is recognised instead of
  being explored twice.
- **The base facts and the invariant signature** — everything a judged world holds besides the
  readings. While that signature is unchanged the tree remains meaningful; once it moves, every
  diff in the tree was measured against a world that is gone.

# What it is not

**Not the [imaginarium](/domain/imaginarium.md).** That is a store and its contents are RDF
graphs. A node carries the NAME of one, so this tree is pointers and that store is what they
point into. Which world has stopped being worth keeping is the cone's to say; performing the
drop is the store's. They begin and end together and answer different questions.

**Not [identification](/domain/identification.md).** That is the act performed upon a cone when
a pass opens, asking where the real world arrived among the imagined ones. This is the thing
asked; identification is the asking.

**Not a [scope](/domain/scope.md).** A scope partitions the vocabulary into compartments no
action couples across. What it settles is HOW MANY of these a want needs — one where the want's
view falls inside a single compartment, several concatenated where it does not — so a scope
counts cones without being one.

# Why it survives a pass

Rebuilding from nothing throws away work the agent already paid for, and most of what a pass
imagines is still true a moment later. So the tree is kept, and the next pass begins by asking
whether the present is among its worlds. Where it is, that world becomes the new root, its
siblings and their subtrees go, and the remaining frontier is what the pass continues from.
Where it is not — another agent moved, the surroundings did, or an action had an outcome the
package never declared — nothing here can be trusted and the tree is abandoned entire.

This is why [budget](/domain/budget.md) is spent in worlds rather than in depth: a pass that
stops at its ceiling has not failed, it has left a frontier for its successor.
