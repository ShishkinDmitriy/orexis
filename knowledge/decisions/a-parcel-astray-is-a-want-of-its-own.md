---
type: Decision
title: A desire over instances says what each block is about, and a parcel astray is a want of its own
description: >-
  The dispatcher world (#567) posed two parcels under one desire that every parcel be delivered,
  and the derivation minted ONE want about both, searched over both vans' every move - 674
  candidates and 85 seconds for a ten-step plan two single-van searches find in 34 and a fifth of a
  second. The courier's delivered shape said nothing of what its one block was about, and a witness
  about nothing is loose and joins every cluster. The shape now says `planning:about sh:this` - each
  block is about the parcel itself - so two parcels astray are two wants, each named for its parcel,
  narrowed to it and planned alone, both delivered in one pass. Refused: a default read off the
  absence, in the derivation; a want about every parcel, which is the product; and two scopes by
  van, which the key cannot give since a parcel is a filling value of both vans' Pick. Closed the
  same day (#893): the estimate was the desire's and counted every parcel, so a want per parcel
  paid for the other van's forks - 61 against 13; the derivation now writes each want's estimate
  with `$this` bound to its parcel, and a want reads its own drives - 37 against 13. The estimate
  then counted the pick and the drop beside the drives (#898) - 23 against 13, and the ten left
  are the one scope's.
status: accepted
timestamp: 2026-10-04T18:00:00Z
---

# Amended 2026-10-05

A parcel astray is a want of its own UNLESS a constraint can couple it to another — the two-vans
aversion reads `at` on vans and joins on the cell, so two parcels whose vans may meet are one cluster,
one want and one search, and the 674-against-90 price this record paid to avoid is paid there and
only there ([one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md)).
Everything below stands for parcels no constraint can join.

# The claim

`derive_wants` clusters a desire's witnesses by the [scope](/domain/planning/scope.md) of what each
is ABOUT, and per instance within it — two tanks low about their level are two wants, two debts two
([one-function-mints-every-want](/decisions/one-function-mints-every-want.md)). A witness is placed
by its `planning:about`, the block's or the desire's; a witness about nothing is placed nowhere and
joins every group, which with one scope is one group. That was the safe side for a desire about one
thing, and it was wrong for a desire about every parcel: the courier's `delivered` shape targets the
class and its one block, `at` equals `destination`, said nothing of what it was about, so the two
parcels of `world/dispatcher/` in trouble were ONE want, about both, narrowed to neither.

The shape now says `planning:about sh:this` on that block — each constraint is about the parcel it
failed on — which is the form the ledger's desire already took for its debts and
`violation._about_each` already read. Under a desire, two parcels astray are then two clusters, two
wants named `every_parcel_delivered.pursued.parcel_a` and `.parcel_b`, each with the shape narrowed
to its parcel as `sh:targetNode`, each searched alone and both delivered in one pass. The courier's
own WANT, which points at the same shape, reads it as before: a want is judged whole, and what a
block is about is read by the derivation alone.

# Measured

One pass of the Planner at a budget of 128 over the booted dispatcher, both vans at the foot of
their own columns and both parcels one cell up (`world/dispatcher/state.ttl`), on the development
container; the figures are in [measure-the-search](/runbooks/measure-the-search.md):

| the delivery desire | wants | candidates | weighings per want | plan | pass |
|---|---|---|---|---|---|
| one block about nothing, budget 128 | one, about both parcels | 128 | 83 | `Exhausted` | 0.73 s |
| the same, budget 1024 | one | 674 | 325 | `Satisfied`, ten steps | 85 s |
| the block about `sh:this`, the desire's estimate, budget 128 | two, one per parcel | 90 | 61 and 64 | two of five steps | 0.55 s |
| the same, each want's estimate bound to its parcel (#893) | two | 90 | 37 and 37 | two of five steps | 0.41 to 0.45 s |
| the same, the estimate counting the pick and the drop (#898) | two | 50 | 23 and 23 | two of five steps | 0.20 to 0.22 s |
| either van and its parcel alone | one | 17 | 13 | five steps | 0.09 s |

The one want is the product: the estimate, drives owed, falls by one for either van's drive toward
its parcel, so every interleaving of the two chains costs the same and the frontier opens them all,
and a budget that finds the corner delivery in 45 candidates does not reach a ten-step plan in 512.
Two wants are each found in five steps, and the dispatcher delivers both in one pass.

# The estimate instantiated at the want (closed 2026-10-04, #893)

The seam this record left: `planning:estimates` pointed at the domain's select, which summed the
drives owed over every parcel astray, and a want narrowed to one parcel inherited it unchanged, so
its `planning:remaining` counted the other parcel's drives too — six where the van alone read three —
and the other van's drive toward its own parcel cost one, saved one, tied the frontier and was
opened. The estimate never overstated the desire's cost and overstated every want's, which is the
one promise an estimate makes. `_narrowed` already instantiated the met-test at the want's instance;
nothing did the same to the select.

The select now speaks of its instance as SHACL's constraints do, `$this` — the one token
`store.bind` lets go unbound — standing where a variable and a name are both legal, the subject of
a pattern and the argument of a `BIND` onto the variable it groups by, never in a projection or a
`GROUP BY`, where a name would not parse. Unbound, for the desire and for the courier's own want, it
is a variable and the sum runs over every parcel; the derivation writes a derived want's own node,
`<want>.estimate`, the desire's select with `$this` bound to the want's instance, beside the
narrowed met-test, and `weigh` reads the want's own node before the desire's as it always did. A
select that names no `$this` — hanoi's disks astray — or a want about several instances points at the
desire's node as before. The derivation's table holds two wants under one desire to two figures,
three and two (`agent/planning/tests/derive_wants/two_parcels_two_estimates.trig`), and the dispatcher's
test holds each want's figure to the van alone's.

Measured, alternated in one session ([measure-the-search](/runbooks/measure-the-search.md)): each
want's weighings fell from 61 and 64 to 37, and `remaining` at the present from six to three. Not to
13; and this section first said the 24 left were not the estimate's to take, since every world a
search opens admits the other van's drives and a candidate admitted is weighed before its estimate
is read. That was right about weighing and wrong about the figure: the select counted the drives
and not the pick or the drop, admissible and loose by two for a standing parcel, so the plan's own
chain stood at three and four on the frontier where the other van's drive stood at four, and the
ties were opened in turn — sixteen of the 37 reached by the other van, eight more of the own van's
reached through them. Counting the pick and the drop (#898) each want reads five at the root, its
plan's own cost, its chain stands at five throughout and the other van's worlds at six, and the
search weighs 23: the van alone's 13 and the other van's two drives admitted in each of the five
worlds it opens. Those ten are what the two-vans seam of
[a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md) costs, and the
seam is unchanged. Refused here: binding the want's `planning:keyedBy` into the select as well — the key is
a tuple of terms the derivation reads off the offending value, no select reads one and no token
names it, and a token nobody reads is annotation; the first estimate that needs a bed rather than a
parcel decides how it is spelled.

# What was refused

- **A default in the derivation: a witness about nothing is about its instance.** It would have
  split the parcels without a word in the shape, and it would have decided by absence — a block that
  says nothing of what it is about would mean "the instance" to the derivation and "nothing" to a
  reader of the shape, which is the kind two readers disagree about. What a block is about is the
  shape's to say, in the one word a block carries beside SHACL's own, and the two shapes that range
  over instances — the ledger's debts, now the courier's parcels — say it.
- **One want about every parcel.** The product, measured above. A want's met-test is the desire's
  instantiated at its witness, and a want about both parcels is the desire itself under another
  name — the universal handed to a search, which
  [a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md)
  refuses.
- **Two scopes, one per van.** The issue's hope, and the key cannot give it: `footprint.atoms_of`
  reads each filling off the public graphs, and a Pick's filling binds a van AND a parcel, either
  van with either parcel, so the atom `(at, van_a)` and the atom `(at, van_b)` are joined through
  `(at, parcel_a)`. Measured: one scope holding both vans, both parcels, every cell, `at`,
  `carriedBy` and the three actions. A key is what the world binds a subject by, and the world
  binds no parcel to a van; the two-vans seam of
  [a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md) says what the
  corridor then showed.

# Seams left open

- **Which van a parcel's want is about is found, not said.** A want per parcel is still searched
  over both vans; the nearest delivers because the estimate says so, and a world where both vans
  are equally near has not been built.
