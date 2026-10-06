---
type: Domain Concept
title: Constraint
term: http://example.org/orexis/planning#Constraint
description: >-
  What a world says of itself is POSSIBLE, stated as a desire is stated - a shape in the same
  words, held by the agent - and of another modality - a desire says what is wanted, a constraint
  what can be. A possible world that violates one is impossible and the search stops there; a
  present that violates one is a contradiction, said and refused, never a want. Its footprint
  couples the wants whose plans it could make collide.
---

# What it is

A [desire](/domain/planning/desire.md) says what the agent wants of the world and a
[precondition](/domain/planning/precondition.md) what one action needs; a **constraint** says what
the world itself allows. The three are checks of different kinds: a met-test asks whether a world
is DESIRED, a precondition whether an action is available, and a constraint whether a world is
POSSIBLE at all. That is a difference of modality and not of strength — desire is bouletic and
possibility alethic — and it is why a constraint is a kind of its own, `planning:Constraint`, and
not a reading of a desire. The dispatcher's is that no cell holds two vans, which is physics and not
a preference: two vans cannot share a cell, and a world where they do is not a bad world the agent
should mend but a world that cannot be.

A constraint is **stated by the world**, in a `planning:ConstraintGraph` (`world/dispatcher/constraints.ttl`),
public as an ontology is, since what is possible is nobody's belief in particular; the agent
`planning:holds` it exactly as it holds a desire, and carries its test in the same two words — a
[shape](/domain/planning/shape.md) under `planning:metWhen`, or the avoided state under
`planning:unmetWhen`, one select whose rows are the instances in it. Either polarity, because the
compiler judges either (`violation.select_of`) and what differs between a desire and a constraint is
what a row MEANS, not how it is found; the prohibition reads most honestly as the avoided state, and
that is the form the dispatcher uses. It is the world's to state and never the agent's to infer, as
every limit here is ([control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)).

SHACL's own word is a second meaning and keeps the word: a shape's *constraint* is one of its
blocks, which `planning:constraint` indexes on a violation row.

# A world that violates one is impossible

`Planner.expand` weighs every constraint of the holder whose footprint the scope's actions write in
each possible world it weighs a want in — the same `weigh`, the same `planning:Weighing` rows — and a
world where any yields a row is marked `planning:impossible` on its own row, naming the constraint.
On the WORLD'S row and not on a weighing, since a world's possibility is true of it whoever asks; the
want's weighing of it is then bare — `planning:open` and `planning:met` taken back, or never written
where another want's search marked the world first — so the frontier's read and the plan's pass it by
by their rows alone, and no filter is asked of either, which #902 measured a quarter of every pass.
The constraint's own weighing stands beside with its rows, so what the world violates can be read.
Nothing compares a child to its parent: possibility is a fact about the world, not about the step
that reached it, so a world that keeps a violation the present already has is as impossible as one
that enters it. The cases are `agent/planning/tests/expand/a_fork_that_violates_a_constraint_is_impossible.trig`
and `a_fork_that_keeps_the_presents_violation_is_impossible_too.trig`; what it does on the
dispatcher's poses, and what it costs a world, is in [measure-the-search](/runbooks/measure-the-search.md).

# The present is validated, never repaired

No want is minted from a constraint: the derivation reads desires alone. A constraint violated in
the present ground is a contradiction between the world's state and its own word about what is
possible, and the pass says so — a warning naming the constraint and its rows, once per scope whose
actions could violate it — and sets about mending nothing; `Planner.contradictions` answers the same
rows to whoever asks, and `orexis-onboard` refuses a world posed that way before anything is granted
(`onboarding/reading.py`, `contradicted`). A prohibition the agent may break and then has to mend
is not a constraint at all but the aversion [desire](/domain/planning/desire.md) describes, and the
suite keeps one being mended in `agent/planning/tests/plans/an_aversions_want_is_repaired_by_a_step.trig`.
The dispatcher's two-vans rule was authored as that until this page said which it was, and two vans
posed on one cell minted a want a drive satisfied: physics mended as a preference.

A limit on ACTS in flight — one driver drives one van at a time — is modelled as world state the
constraint can read, a driver who must be aboard the van it drives, or not at all; an executor-held
resource over committed steps' windows, `execution:occupies`, was built and refused
([one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md)).
`world/driver/` is that state, and its constraint that a driver is aboard one van is broken by no
plan and held for its footprint alone, which the record's driver seam explains.

# Its footprint, and why it is read over the reach

A constraint's select has a [footprint](/domain/planning/footprint.md) as any text does, the
predicates it reads; and, as a [scope](/domain/planning/scope.md)'s atoms do, it has a KEY - the
variable its patterns share, the cell both `courier:at` patterns end in. What it joins there is
what it can make collide: two plans whose steps write `at` on two vans that can stand on one cell.

It is not read where a scope's atoms are. A scope asks each precondition over the public graphs
with every pattern optional, which is right for a partition fixed at boot, and asked that way the
constraint is grid-blind: it joins `van_a` to `van_b` with the cell unbound on the shipped
dispatcher and on a variant whose vans stand on two grids a continent apart alike, four identical
rows, because which cells a van can stand on is the drive's `FILTER` over coordinates and the
public half of a text is its patterns alone (measured, `agent/planning/tests/test_couplings.py`).
So the select is asked over the **reach** - every fact some sequence of the actions could make
true from the present ground with nothing taken away, the delete-free closure of the effects'
constructs over their preconditions, which is the planning literature's relaxed reachability.
Over the reach the constraint's rows are the collisions the plans could actually make: thirty-two
on the shared 4x4, none on two grids, in seven rounds and twelve milliseconds. Each row's bound
IRIs are joined into one part - the vans that can meet and the cells they meet on - and an instance
reaches a part through a FILLING the reach admits that binds both, the pick of this parcel into
that van, exactly as a scope's key is what the world binds a subject by. Two instances are coupled
where one part meets what each is, or is bound with. Over-approximation is the safe side
throughout: a constraint whose select will not compile or run couples everything.

The reach begins at the present, since where the vans stand decides which grid each is on, so this
is read PER PASS in the derivation and never at boot (`agent/planning/couplings.py`); a holder with
no constraint pays one query and couples nothing, and the dispatcher pays the reach, measured in
[measure-the-search](/runbooks/measure-the-search.md).

# What coupling does

`derive_wants` groups a desire's witnesses by scope and instance as before and then merges two
groups of one scope over one stretch whose instances a constraint couples, transitively: one want
about both, named for both, its met-test targeting each instance by `sh:targetNode`, searched
once, in which the colliding world is impossible rather than found afterwards. Its
estimate is the desire's select unbound, the sum over every instance astray, which is the joint
plan's cost where the coupled instances are all there are - and counts a third instance coupled to
neither, the overstatement the record below carries as a seam. Instances no constraint joins stay
apart exactly as [a-parcel-astray-is-a-want-of-its-own](/decisions/a-parcel-astray-is-a-want-of-its-own.md)
left them. A coupled cluster that takes in an instance a walking want is about reopens that want,
which is the one trigger of soft [commitment](/domain/execution/commitment.md).
`agent/planning/tests/derive_wants/two_parcels_a_constraint_joins_are_one_want.trig`
and `two_parcels_on_disjoint_grids_are_two_wants.trig` hold the derivation to both;
`world/dispatcher/tests/test_dispatcher.py` holds the world to the joint ten-step plan and to the
product it costs. The argument, and what was refused in its place, is
[one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md).
