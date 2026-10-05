---
type: Domain Concept
title: Constraint
description: >-
  What a plan may not do, however the want is met - in two kinds, a state invariant and a
  resource. No term of its own - an invariant IS a standing desire in its avoided-state form, read
  twice more than a desire is - as a bound on every possible world a search opens, and, through
  its footprint over what the actions can reach from the present, as what couples two wants
  into one search. The dispatcher's aversion joins two parcels whose vans can meet and leaves two
  on separate grids apart.
---

# What it is

A desire says what the agent wants of the world and a [precondition](/domain/planning/precondition.md)
what one action needs; a **constraint** is what no plan may bring about on its way, whichever want it
serves. Two kinds, checked in two places:

- a **state invariant** - *no cell holds two vans* - a condition on the world a plan must keep at
  every step, judged in the possible worlds a search opens;
- a **resource** - *one driver drives one van at a time* - a limit on the ACTS in flight rather than
  on a state, judged over committed steps' windows. Named here and built by #903; nothing shipped
  declares one yet.

Both are the world's to state and never the agent's to infer, which is the one rule the architecture
applies to every limit - a cadence, a range, what is available
([control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)).

# No term of its own

A state invariant is a `planning:Desire` carrying `planning:unmetWhen`, the aversion's honest form,
exactly as [desire](/domain/planning/desire.md) describes it, and nothing more is declared. The code
finds a holder's constraints by that word, which every aversion already carries and `weigh` already
reads; a `planning:Constraint` beside it would say the same thing twice, and the day the two
disagreed - a desire typed a constraint with a met-test, an aversion typed none - the search would
believe one and the derivation the other. So *constraint* names a READING of a desire: the derivation
reads an aversion as what may couple two wants, the search as what may refuse a world (#902), and the
same node is still the desire whose unmet rows mint a want when the avoided state already holds. A
resource, once built, is to be stated by the world in the same form, one select over committed
steps' windows, for the same reason - a limit derived from an action's taker would be the agent
inferring what it may do from who carries a step out, and no courier action names a taker at all,
a drive being fictive.

SHACL's own word is a second meaning and keeps the word: a shape's *constraint* is one of its
blocks, which `planning:constraint` indexes on a violation row.

# Its footprint, and why it is read over the reach

A constraint's select has a [footprint](/domain/planning/footprint.md) as any text does, the
predicates it reads; and, as a [scope](/domain/planning/scope.md)'s atoms do, it has a KEY - the
variable its patterns share, the cell both `courier:at` patterns end in. What it joins there is
what it can make collide: two plans whose steps write `at` on two vans that can stand on one cell.

It is not read where a scope's atoms are. A scope asks each precondition over the public graphs
with every pattern optional, which is right for a partition fixed at boot, and asked that way the
aversion is grid-blind: it joins `van_a` to `van_b` with the cell unbound on the shipped
dispatcher and on a variant whose vans stand on two grids a continent apart alike, four identical
rows, because which cells a van can stand on is the drive's `FILTER` over coordinates and the
public half of a text is its patterns alone (measured, `agent/planning/tests/test_couplings.py`).
So the select is asked over the **reach** - every fact some sequence of the actions could make
true from the present ground with nothing taken away, the delete-free closure of the effects'
constructs over their preconditions, which is the planning literature's relaxed reachability.
Over the reach the aversion's rows are the collisions the plans could actually make: thirty-two
on the shared 4x4, none on two grids, in seven rounds and twelve milliseconds. Each row's bound
IRIs are joined into one part - the vans that can meet and the cells they meet on - and an instance
reaches a part through a FILLING the reach admits that binds both, the pick of this parcel into
that van, exactly as a scope's key is what the world binds a subject by. Two instances are coupled
where one part meets what each is, or is bound with. Over-approximation is the safe side
throughout: a constraint whose select will not run couples everything.

The reach begins at the present, since where the vans stand decides which grid each is on, so this
is read PER PASS in the derivation and never at boot (`agent/planning/couplings.py`); a holder with
no aversion pays one query and couples nothing, and the dispatcher pays the reach, measured in
[measure-the-search](/runbooks/measure-the-search.md).

# What it does

`derive_wants` groups a desire's witnesses by scope and instance as before and then merges two
groups of one scope over one stretch whose instances a constraint couples, transitively: one want
about both, named for both, its met-test targeting each instance by `sh:targetNode`, searched
once, in which the invariant can refuse a colliding world rather than find it afterwards. Its
estimate is the desire's select unbound, the sum over every instance astray, which is the joint
plan's cost where the coupled instances are all there are - and counts a third instance coupled to
neither, the overstatement the record below carries as a seam. Instances no constraint joins stay
apart exactly as [a-parcel-astray-is-a-want-of-its-own](/decisions/a-parcel-astray-is-a-want-of-its-own.md)
left them. `agent/planning/tests/derive_wants/two_parcels_a_constraint_joins_are_one_want.trig`
and `two_parcels_on_disjoint_grids_are_two_wants.trig` hold the derivation to both;
`world/dispatcher/tests/test_dispatcher.py` holds the world to the joint ten-step plan and to the
product it costs. The argument, and what was refused in its place, is
[one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md).
