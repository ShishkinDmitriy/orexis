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
  van, which the key cannot give since a parcel is a filling value of both vans' Pick. Left open:
  the estimate is the desire's and counts every parcel, so a want per parcel pays for the other
  van's forks - 61 against 13.
status: accepted
timestamp: 2026-10-04T18:00:00Z
---

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
| the block about `sh:this`, budget 128 | two, one per parcel | 90 | 61 and 64 | two of five steps | 0.55 s |
| either van and its parcel alone | one | 17 | 13 | five steps | 0.09 s |

The one want is the product: the estimate, drives owed, falls by one for either van's drive toward
its parcel, so every interleaving of the two chains costs the same and the frontier opens them all,
and a budget that finds the corner delivery in 45 candidates does not reach a ten-step plan in 512.
Two wants are each found in five steps, and the dispatcher delivers both in one pass.

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

- **The estimate is the desire's and counts every parcel.** `planning:estimates` points at the
  domain's select, which sums the drives owed over every parcel astray; a want narrowed to one
  parcel reads the other's drives in its `planning:remaining` too, so the other van's drive toward
  its own parcel costs one and saves one, ties the frontier, and is forked: 61 and 64 weighings
  per want against 13 for the van alone. The estimate never overstates the desire's cost and does
  overstate the want's, and nothing instantiates a select at a want's instance as `_narrowed` does
  a shape. That is a defect of the per-instance want, and an issue, not a seam of this record.
- **Which van a parcel's want is about is found, not said.** A want per parcel is still searched
  over both vans; the nearest delivers because the estimate says so, and a world where both vans
  are equally near has not been built.
