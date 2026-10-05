---
type: Domain Concept
title: Constraint
description: >-
  What a plan may not do, however the want is met - in two kinds, a state invariant and a
  resource. No term of its own - an invariant IS a standing desire in its avoided-state form, read
  twice more than a desire is - as a bound on every possible world a search opens, and, through
  its footprint over what the actions can reach from the present, as what couples two wants
  into one search; a resource is one row the world states of an action, what its act holds while
  in flight, which the executor honours by offering no second head while one holds it. The
  dispatcher's aversion joins two parcels whose vans can meet and leaves two on separate grids
  apart, and its one driver walks two plans a drive at a time.
---

# What it is

A desire says what the agent wants of the world and a [precondition](/domain/planning/precondition.md)
what one action needs; a **constraint** is what no plan may bring about on its way, whichever want it
serves. Two kinds, checked in two places:

- a **state invariant** - *no cell holds two vans* - a condition on the world a plan must keep at
  every step, judged in the possible worlds a search opens and refusing one that newly enters the
  avoided state (#902);
- a **resource** - *one driver drives one van at a time* - a limit on the ACTS in flight rather than
  on a state: what an action's act holds from being handed to its taker until the world answers it,
  which the world states of a domain's action with `execution:occupies` and the executor honours by
  handing no second head over while one holds it (#903). The dispatcher declares one driver whom
  every drive, pick and drop occupies.

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
reads an aversion as what may couple two wants, the search as what may refuse a world, and the
same node is still the desire whose unmet rows mint a want when the avoided state already holds.

A resource is NOT a desire, and this page first said it would be - one select over committed steps'
windows, in the aversion's form. Built (#903), that form could judge nothing: a committed step is
believed over its landing window AS THE PLAN PLACED IT, and two plans placed in one pass for one
driver both open at the pass's instant, so their windows overlap whether or not either act has begun
- the overlap is the plans' bands, not the acts' occupancy - and a desire reading it would have
minted an unreachable want every pass while the executor serialised the very acts it complained of.
What *in flight* means - handed over or taken, and not yet answered - is written nowhere but the
intentions, which no met-test is handed. So a resource is one row the world states of a domain's
action, `execution:occupies`, naming the node held - the one driver - or a parameter the action
takes, and then the step's own value for it, which is how a world says a driver per van; execution's
word, since what is held while an act is in flight is a fact about taking the action, as its
implementation is. It is still the world's and never derived from the action's taker, since a limit
inferred from who carries a step out would be the agent deciding what it may do, and no courier
action names a taker at all, a drive being fictive.

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

**As a bound, in the search.** `Planner.expand` weighs each state invariant of the holder in every
possible world it weighs a want in — the same `weigh`, the same rows — and refuses a world whose
weighing carries a violation row with no equal in its parent's: `planning:refused` on the want's
weighing names the invariant and replaces the verdict, `planning:open` and `planning:met` taken
back, so the frontier and the plan pass the weighing by with no filter asked of either, whatever
the want's own test said there. The invariants weighed in a scope are those whose
select reads a predicate the scope's actions write; one that reads none is kept by every world and
costs nothing. A world that merely keeps a row the root already had is not refused, which is why
two vans posed on one cell still mint the aversion's want and a drive parts them. The cases are
`agent/planning/tests/expand/a_fork_that_newly_enters_the_avoided_state_is_refused.trig` and
`a_fork_that_keeps_a_violation_the_root_already_had_is_not_refused.trig`; what it did to the
dispatcher's poses, and what it costs a world, is measured in
[measure-the-search](/runbooks/measure-the-search.md). Why never-newly-enter and not a precondition
or an executor's hold is the record's.

**As a limit on acts, in the executor.** `Executor.tick` reads what each standing head's action
occupies before it offers any head, and a head due whose resource another head holds - handed over
this tick, or taken and not yet answered - is passed over, as a head before its `execution:notBefore`
is, with nothing recorded of the wait; heads are offered in the order they fell due and then the
order their intentions were adopted, so the elder plan drives first. The hold ends when the holding
step is answered, which is when its [committed step](/domain/execution/committed-step.md)'s window
closes. A holder with one intention standing is asked nothing, since a plan is a chain and a chain
never has two acts in flight; one with several pays two queries a tick. On the dispatcher's two grids
with one driver the two plans' drives alternate where they ran in lockstep, and with a driver per van
they run in parallel again (`world/dispatcher/tests/test_dispatcher.py`,
`agent/execution/tests/test_executor.py`). **The search has nothing to refuse here**: a step of a
chain opens where the one before it lands, so no path a search makes holds two acts of one resource
at once, and the day a plan is a partial order is the day the resource is read over a world's path
(the record's concurrent-steps seam).

**As what couples, in the derivation.** `derive_wants` groups a desire's witnesses by scope and instance as before and then merges two
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
