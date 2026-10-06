---
type: Runbook
title: Measure the search
description: >-
  How to time the planner on its bench - two hanoi puzzles and the courier's corner delivery,
  held to their plans and timed as the median of five passes - how to record a row in the
  ledger, and what the measurements so far say. Numbers are commits, not impressions - every
  row names what ran and where.
---

# Why these cases are the bench

A hanoi puzzle and a courier delivery are all search: no bus, no sensors, no containers — one
want, a handful of actions, and the plan is the whole cost. A change that moves these numbers
moved the planner, not the weather. See
[the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md).
What a whole agent pays per reading on a shipped world — sensing and revision and the executor
around the search — is the other bench's, [measure-a-pass](/runbooks/measure-a-pass.md); the
greenhouse figures below are the Planner's alone.

# How to measure

```bash
pytest agent/planning/tests/test_bench.py -s -n0                 # print the figures
pytest agent/planning/tests/test_bench.py -s -n0 --bench-record  # and append them to the ledger
python -m cProfile -o /tmp/bench.prof -m pytest agent/planning/tests/test_bench.py -n0 -q
```

`agent/planning/tests/test_bench.py` asserts the plans — three moves for two disks, seven for
three, eight steps for the parcel — and reports the median of five passes with the count of
engine statements beside it. No time is asserted. cProfile roughly doubles everything, so a
profile is for SHARES and the plain run is for the ledger.

**A/B is alternated within one session or it is not a measurement.** The bench Pi drifts about
twofold between invocations, and two trees timed minutes apart made a change that does nothing
read as a thirty-percent win.

# The ledger

**The ledger is `agent/planning/tests/bench/results.tsv`**, one row per case per
recorded run: the date, the commit (`-dirty` where the tree had uncommitted changes), the
machine, the case, the budget, the runs, the median and minimum milliseconds, the queries and
updates of one pass, and the steps of the plan. It is appended, never rewritten, so the series
is the history; a row is a measurement because it names its commit and its machine. Two
trees are compared alternated in one session, never minutes apart, and the ledger
holds each tree's own rows rather than a difference somebody computed once.

The first rows: at `3163346d` on the bench Pi, two disks in about 45 ms over 137 queries and
three disks in about 170 ms over 383 queries, the three-disk pass having come down from 645 ms
in the same day by binding the catalogue once and narrowing what an iteration reads. The
tree before it, `463e27c5`, ran two disks in about 30 ms and could not reach three within its
fixed budget.

**Against the predecessor, alternated in one session (2026-09-23, the bench Pi):** the pass
of `packages/orexis-agent-deliberation/` over `world/hanoi` — `considering` and then the
search — against the whole pass here, a fresh store per run, medians of five:

| disks | predecessor, considering + search | planning package, whole pass |
|---|---|---|
| 3 | 144 + 415 ms | 194 ms |
| 2 | 143 + 244 ms | 50 ms |

The predecessor's row above says 0.31 s for three disks and its search took 0.42 s on the day
this was taken, which is the drift the table warns about and why the two sides are timed
together here. Inside the package the star cost something too: the tree before it,
`463e27c5`, ran two disks in about 30 ms against 45 alternated the same day, and could not
reach three disks within its fixed budget of 32.

**A second pass, with the imaginarium kept (2026-09-23, the bench Pi, alternated in one
session):** the same three-disk case planned once, then planned again a minute later on the
same Planner against a fresh one, medians of five:

| pass 2 | imaginarium kept | fresh Planner |
|---|---|---|
| nothing happened | 42 ms | 156 ms |
| after the plan's first move | 34 ms | 132 ms |

What the kept pass does is refresh the copy, lay the new present, identify it by hash among the
worlds of the last pass (`reroot`), and read its way to the plan without forking; the first
pass pays for that machinery in statements — two disks 152 queries and 61 updates against 137
and 59 before, three disks 412 and 215 against 383 and 213 — and not measurably in time. The
same day, the read that lists the candidates still to weigh cost 74 ms on the kept cone and
answered nothing, because its `NOT EXISTS` scanned every weighing per candidate; with the bound
variable first it costs 4, which is the difference between the kept pass at 178 ms, slower than
fresh, and at 42.

**The estimate returned (2026-09-23), and a third bench case with it.** `orexis:estimates`
on a want, or on the desire it was derived from, points at the package's select; `weigh`
writes what it reads as `planning:remaining` on the weighing, and the frontier orders by
spent plus remaining with the bound on the sum. `courier_corner` is the corner delivery from
`world/courier/`, eight steps, assembled as the hanoi cases were. Alternated in one session,
budget 128, candidates weighed and the median of five:

| case | with the estimate | without |
|---|---|---|
| three disks | 50 candidates, 131 ms | 56 candidates, 139 ms |
| courier corner | 45 candidates, 128 ms | 128 candidates, 392 ms, EXHAUSTED |

Without the estimate the corner delivery spends the whole budget and answers with no plan;
given 512 it arrives after 198 candidates in 846 ms, which is the predecessor's 198 exactly,
against 45 here where the predecessor had 78. Hanoi's estimate is weak, disks astray, and
buys a tenth; the courier's is the drives owed and buys the plan.

**A search cut by the budget is finished by the passes after (2026-09-23).** Three disks at a
budget of twenty a pass, one pass a minute on one Planner: 20, 40 and 50 candidates weighed
after each pass, EXHAUSTED twice with nothing handed down, the seven-move plan and its
intention on the third, at 65, 77 and 69 ms a pass against 131 for the search in one. The sum
is the one-shot search's 50 exactly, and a fourth pass, the want being walked, weighs nothing
in 24 ms. `agent/planning/tests/test_planner.py` holds the equality.

**Refused on measuring, the same day: spelling the catalogue's name.** Every `?cat` in every
statement replaced by the constant at the engine's door — the shape a hardcoded singleton
graph would give a reader — ran three disks at 163 ms against 168 as it is, inside one
session's noise, with 885 statements rewritten. The profile says why: of a 194 ms pass under
cProfile, 86 ms is the engine evaluating 381 queries and 25 ms its 213 updates, about 0.23 ms
a query, and finding one row by its class inside a bound graph is no measurable part of a
query; what a pass pays for is the COUNT of statements, which is the star's price — each act
reads its inputs back off the rows the last act wrote, and what would move the figure is
fewer reads, not shorter ones.

# The greenhouse: one scope against two (2026-10-04)

The measurement #593 asked for, on the cold dry bed — the thermometer at 12 and the probe at 0.2,
both below the bed's ranges — one pass of the Planner at a budget of 128 over the booted world,
the two trees alternated in one session on the development container:

| partition | imaginaria | worlds forked | weighings | plans | pass |
|---|---|---|---|---|---|
| over predicates, `ef8b912` | 1 | 4 | 6 | one want, two steps | 58 ms |
| over keys, this tree | 2 | 1 + 1 | 3 + 3 | two wants, one step each | 107 ms |

The sum against the product: both levers in one cone forked the dose, the heating and each after
the other before the two-step plan was found; apart, each cone forked its one step. The pass costs
nearly twice as much, and the whole of the difference is the second imaginarium's filling —
`prepare_ground` copies the beliefs once per scope — which is a fixed price per scope while the
worlds saved grow with the depth of the plans. The knob regime, a heater that dries the soil, has
no shipped world; `agent/planning/tests/scope_actions/a_heater_that_dries_the_soil.trig` holds it to one
scope.

# What a world costs against the present, and what an unrelated aspect costs a want (2026-10-04)

The two metrics the sovereign named, held by `world/greenhouse/tests/test_scaling.py`. The cold dry
bed as above, then the same world with a light sensor on the bed, a lamp that raises it and a desire
that the bed be lit — an aspect nothing of the soil or the air touches:

| | present store | readings + sides | soil's ground / world | scopes | soil's search |
|---|---|---|---|---|---|
| greenhouse as shipped | 1248 quads | 24 | 12 | 2 | 1 world, 1 candidate of 1 action |
| with light, lamp and a lit desire, the bed dim | 1335 | 35 | 12 | 3 | 1 world, 1 candidate of 1 action |

A possible world is the SCOPE's readings and the sides concluded of them, forked from a ground that
holds those alone, and no public knowledge: one percent of the present. The unrelated aspect left the
soil's search as it was — the same world of the same twelve quads over the same one candidate — and
the lamp, a second filling of the heating action, which is in the air's scope and the light's, is
admitted in the light's search alone and its step judged there alone, since a scope admits a FILLING
and not an action. Before the readings were parted by scope the soil's world was 24 quads and grew to
35 with the light's reading, which the soil never reads; before a scope admitted fillings, the air's
search forked the lamp's heating too, two candidates where one is its own. Every figure in the
soil's columns is now flat under the aspect added.

# Two beds, two pumps: two instances of one property (2026-10-04)

The two-instances seam of [a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md),
measured closed. The shipped greenhouse against the same world with a second bed, probe and pump
added (`world/greenhouse/tests/test_two_beds.py`), every soil at 0.2 and the air warm at 21, one
pass of the Planner at a budget of 128 over the booted world, the two alternated in one session on
the development container, medians of five:

| world | present store | readings + sides | imaginaria | grounds | worlds forked | weighings | plans | pass |
|---|---|---|---|---|---|---|---|---|
| one bed | 1263 quads | 24 | 2 | 12 + 12 | 0 + 1 | 1 + 3 | `pursued.SoilMoisture`, one step | 65 ms (min 58) |
| two beds | 1357 | 36 | 3 | 12 + 12 + 12 | 0 + 1 + 1 | 1 + 3 + 3 | `pursued.bed.SoilMoisture` and `pursued.bed2.SoilMoisture`, one step each | 121 ms (min 104) |

Each soil scope's ground is its own bed's reading and sides, twelve quads, and the air's its
thermometer's; the first bed's reading, which is the pump's scope's and the heater's by the bed and
the first pump's by the property, crosses into the first pump's imaginarium alone. The second bed
costs what a scope costs — a filling of the imaginarium and one weighing of the desire — and both
pumps are commanded in the one pass. On the tree before, the same world minted `pursued.SoilMoisture`
in all three imaginaria, placed it in the first, reported it unreachable and commanded nothing.

# The dispatcher: two vans in one scope (2026-10-04)

The measurements #567 asked for, on `world/dispatcher/` — one agent, two vans, two parcels on the
courier's 4x4 grid, a desire that every parcel be delivered and an aversion to two vans on one cell —
taken on the development container with the tree that added the world, one pass of the Planner at a
budget of 128 over the booted world unless a budget is named, medians of five where a time is given.
`world/dispatcher/tests/test_dispatcher.py` holds every claim below but the times.

**The partition.** One scope: both vans, both parcels, every cell, `courier:at`, `courier:carriedBy`
and the three actions. Nothing van A does reads a fact about van B, and the key cannot see it: a
Pick's filling binds a van and a parcel, either with either, so the two vans' atoms are joined
through each parcel's ([a-parcel-astray-is-a-want-of-its-own](/decisions/a-parcel-astray-is-a-want-of-its-own.md)).

**Apart** — each van at the foot of its own column, its parcel one cell up, owed at the top; the two
chains share no cell — against each van and its parcel alone in a world of its own:

| world | wants | candidates | weighings per want | plans | pass |
|---|---|---|---|---|---|
| both vans, the delivery shape's block about nothing | one, about both parcels | 128 of a budget of 128 | 83 | `Exhausted` | 731 ms |
| the same at a budget of 1024 | one | 674 | 325 | one plan of ten steps, `Satisfied` | 85 s |
| both vans, the block about `sh:this`, the desire's estimate | two, one per parcel | 90 | 61 and 64 | two plans of five steps | 545 ms |
| van A and parcel A alone | one | 17 | 13 | five steps | 88 ms |
| van B and parcel B alone | one | 17 | 13 | five steps | 87 ms |

Weighings per want are of possible worlds; a candidate passed over is weighed too and not counted.
The sum the issue hoped for is 26 weighings over 34 candidates; the product over one want is 325
over 674 and finds the same ten steps; a want per parcel was between, 125 over 90, because each
want's search still forked the other van — the estimate was the desire's and counted both parcels,
so the other van's drive toward its parcel tied the frontier. That is the figure #893 closed, below.
Through the runtime, the shipped world delivers both parcels in one pass, ten acts.

**The corridor** — van A drives parcel A along the second row, van B drives parcel B down the third
column, and the two shortest chains meet at `c2_1` at each van's third step (the test's variant of
the world). One pass with the desire's estimate: two wants, two plans of five steps, 87 and 92
weighings over 118 candidates, each plan driving its van to `c2_1`; of the 118 worlds the searches
visited, FOUR held two vans on one cell, and the aversion was weighed in none of them — a desire is
weighed in grounds alone, and in the present the vans stood apart, so no want was minted from it.
Walked, the two intentions alternate steps within the one pass, and after the sixth act BOTH VANS
STAND ON `c2_1` in the agent's beliefs, for one act; the next pass finds both parcels delivered and
nothing to mint. The delivered plans put two vans on one cell, and nothing saw it: the derivation
runs in the planner's pass, the walk comes after it, and the state between two steps is judged by
nobody.

# The dispatcher: a want's estimate bound to its parcel (2026-10-04, #893)

The apart figures above re-measured with each want's estimate instantiated at its parcel — the
courier's select written with `$this` for the parcel, and the derivation writing each want's own
node with `$this` bound (a-parcel-astray-is-a-want-of-its-own, the closed seam). Same world, same
budget of 128, the two trees alternated twice in one session on the development container, medians
of five; `remaining` is what each want's estimate read in the present ground:

| world | estimate | candidates | weighings per want | reached by the other van | `remaining` | pass |
|---|---|---|---|---|---|---|
| both vans, apart | the desire's, every parcel | 90 | 61 and 64 | 29 and 28 | 6 and 6 | 635 ms, then 498 (min 551, 474) |
| both vans, apart | the want's, its parcel | 90 | 37 and 37 | 16 and 16 | 3 and 3 | 449 ms, then 409 (min 385, 365) |
| either van and its parcel alone | either, one parcel | 17 | 13 | — | 3 | 80 to 98 ms, both trees |
| the corridor | the desire's | 118 | 87 and 92 | 42 and 42 | 6 and 6 | 821 ms, then 954 |
| the corridor | the want's | 140 | 58 and 58 | 22 and 22 | 3 and 3 | 832 ms, then 821 |

Each want reads what the van alone reads, three drives, where it read the sum. The weighings fell
from 61 and 64 toward 13 and stopped at 37, and the 24 over the van alone are the one scope's price
that an estimate cannot pay: every world a search opens admits the other van's two or three drives,
a candidate admitted is weighed — that is where `remaining` is read — and the estimate orders the
frontier and refuses to OPEN a world, never to weigh one. Sixteen of each want's 37 worlds were
reached by the other van's move; with the desire's estimate the other van's drive cost one and saved
one, so those worlds tied the frontier at the plan's own cost and were opened in turn, and 29 of
61 were the other van's. The other van's drive now costs one and saves nothing, so its worlds stand
at the plan's cost or past it and are opened only where the tie-break reaches them before the plan
is found. This section first read the whole 24 as the one scope's price and said a better estimate
could not take it away, which the next section found wrong by fourteen: the estimate counted the
drives and not the pick or the drop, and the slack was where the ties came from. On the corridor
the searches no longer visit a world with two vans on one cell — none of 140, against four of 118
— and the two still meet on `c2_1` when the plans are walked, which is the finding that mattered
and is unchanged.

# The dispatcher: the pick and the drop counted (2026-10-04, #898)

`courier:drivesOwed` summed the drives a parcel still needed and nothing else — admissible, and loose
by one for a carried parcel and two for a standing one, since every courier action costs one and a
parcel not at its door is dropped exactly once, one not yet carried picked exactly once. The select
now adds them. The cases above re-measured, the two trees alternated twice in one session on the
development container, medians of five; every count was identical across the four rounds, and the
before tree reproduces the section above exactly. `remaining` is what each want's estimate read in
the present ground, beside what the plan it got spent:

| world | estimate | candidates | weighings per want | reached by the other van | `remaining` | plan spent | pass |
|---|---|---|---|---|---|---|---|
| both vans, apart | the drives alone (#893) | 90 | 37 and 37 | 16 and 16 | 3 and 3 | 5 and 5 | 439 ms, then 415 (min 426, 390) |
| both vans, apart | the drives, the pick and the drop | 50 | 23 and 23 | 10 and 10 | 5 and 5 | 5 and 5 | 220 ms, then 204 (min 204, 185) |
| either van and its parcel alone | the drives alone | 17 | 13 | — | 3 | 5 | 91 to 106 ms |
| either van and its parcel alone | with the pick and the drop | 17 | 13 | — | 5 | 5 | 81 to 98 ms |
| the corridor | the drives alone | 140 | 58 and 58 | 22 and 22 | 3 and 3 | 5 and 5 | 835 ms, then 869 (min 741, 806) |
| the corridor | with the pick and the drop | 68 | 33 and 33 | 15 and 15 | 5 and 5 | 5 and 5 | 290 ms, then 302 (min 273, 293) |
| the courier's own delivery, `world/courier/` | the drives alone | 45 | 26 | — | 6 | 8 | 143 ms, then 169 |
| the courier's own delivery | with the pick and the drop | 45 | 26 | — | 8 | 8 | 162 ms, then 167 |

**Of the 24 over the van alone, 14 were the estimate's and 10 are the one scope's.** At the root each
want's estimate now reads what its plan will cost, five, and every world on the plan's own chain
stands at five too: the drive toward the parcel costs one and saves one, the pick costs one and turns
the standing parcel's two into the carried parcel's one, the drop costs one and saves the last one.
The other van's drive costs one and saves nothing, so its worlds stand at six and are never opened
before the plan is found. They are still admitted and weighed — two drives of the other van in each
of the five worlds the search opens, ten — and that is the whole of what the one scope now costs:
23 is the van alone's 13 plus those ten. With the drives alone the plan's chain stood at three and
four, the other van's worlds at four, and the ties were opened in turn: sixteen of the other van's
and, reached through them, eight more of the own van's, which is the fourteen. The two-vans seam of
[a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md) carries the ten.

**The courier alone does not move**, and that is the measurement's other half: with one van, every
step of the plan keeps the frontier key where it is and every step off it raises it by two, under
either estimate; the pick and the drop shift the key by the same amount at every world of a stretch,
so the order the frontier opens in is the same and the 45 candidates are the same 45. The bench's
`courier_corner`, its fixture brought to the domain's text, ran 476 queries and 169 updates on both
trees — the count does not drift — at 150 and 144 ms before against 155 and 159 after, which is
inside one session's noise. The tower's estimate is hanoi's and is untouched.

**The promise is a gate now.** `world/dispatcher/tests/test_dispatcher.py` and
`world/courier/tests/test_courier.py` each hold the `planning:remaining` written at the present
ground to at most what the plan spent, over the shipped dispatcher, its corridor, a van alone and
the courier's delivery; broken by ten on purpose, every case went red at that line.

**Both vans on one cell at a pass's start** — van B posed on van A's cell: the aversion reads unmet
for each van, one want `no_cell_holds_two_vans.pursued` is minted, about both vans, and a one-step
plan — a drive — satisfies it in 4 weighings. Measured first with the aversion authored as a
met-test over a `sh:sparql` constraint, because authored as `planning:unmetWhen`, as #567 asks,
the desire was then weighed in no ground at all — `weigh` read a met-test through
`planning:metWhen` and nothing else, and the pass minted nothing from it. Since #892 the shipped
aversion IS the `unmetWhen` form, the avoided state as one select, and the figures are the same:
a witness per van offending with the cell, the one want carrying the same select, the one-step
plan, 4 weighings (measured 2026-10-04, pinned in `world/dispatcher/tests/test_dispatcher.py`).

# The dispatcher: what a bound on worlds would cost, a parked van, and the coupled price (2026-10-04)

The measurements [one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md)
stands on (its first version, sequencing the plans, was refused the next day for the coupled search; the figures were taken for both), taken on the development container with the tree at `1f98dc14`, one pass of the Planner
at a budget of 128 over the booted world as the test builds it; not in the suite, since the
mechanism they measure — the bound — is decided and not built. The coupling is built, and its
figures are the next section's.

| case | wants | weighings | worlds | holding two vans | the aversion weighed in every world | walked |
|---|---|---|---|---|---|---|
| the corridor | 2 | 33 and 33 | 68 | 0 | 38.4 ms (min 37.7 of five), 0.56 ms a world, unmet in 0 | both on `c2_1` for one act |
| van B parked on `c2_1`, parcel A owed at `c3_1` from `c1_1` | 1 | 58 | 66 | 11 | unmet in 11 | both on `c2_1` for one act |

**Every world and every step of the corridor stands at one instant** — the pass's, for both ends of
each of the 68 worlds' periods and for the ten steps' `notBefore`, `landsAt` and `notAfter` alike —
because the courier declares no `planning:landsAfter`; so the two plans have no instant to be
composed at. **After the runtime's pass the beliefs hold two plan graphs and nothing else of the
walk**: no committed step (every window closed and swept inside the pass), no prediction, no drift,
no sensor. The parked van is the case a bound on worlds refuses and the corridor the case it
cannot: the plan through the parked van visits eleven worlds that hold two vans, where the two
corridor plans, each moving its own van, visit none.

# The dispatcher: the wants the aversion couples, searched as one (2026-10-05, #900)

The derivation couples two instances a [constraint](/domain/planning/constraint.md) can make collide
into one want, and the dispatcher's aversion — `at` on vans, joined on the cell — couples its two
parcels wherever both vans can reach one cell. Measured on the development container, the tree before
the change (`c8cd7ad1`) and the tree with it alternated per case in one session, five rounds, one pass
of the Planner over the booted world as `world/dispatcher/tests/test_dispatcher.py` builds it, each
tree at the budget its search needs; candidates are the possible worlds the pass made, weighings the
worlds weighed per want. The counts did not move between rounds on either tree.

| pose | tree | budget | wants | candidates | weighings per want | plan | pass, median of five (min) | worlds holding two vans |
|---|---|---|---|---|---|---|---|---|
| apart, as shipped | before | 128 | two, one per parcel | 50 | 23 and 23 | two of five steps | 206 ms (171) | 0 |
| apart, as shipped | after | 128 | ONE, about both | 128 of 128 | 87 | `Exhausted` | 708 ms (668) | 0 |
| apart, as shipped | after | 256 | one | 228 | 148 | one of ten steps | 2577 ms (2488) | 0 |
| the corridor | before | 128 | two | 68 | 33 and 33 | two of five steps | 295 ms (262) | 0 |
| the corridor | after | 512 | one | 296 | 216 | one of ten steps | 5272 ms (4973) | 18 |
| the vans on disjoint grids | before | 128 | two | 50 | 23 and 23 | two of five steps | 196 ms (182) | 0 |
| the vans on disjoint grids | after | 128 | two | 50 | 23 and 23 | two of five steps | 258 ms (211) | 0 |

**The coupled search pays the product and finds the joint optimum.** Ten steps for 228 candidates on
the shipped pose, against the 674 the same coupled want cost before the estimate was bound to its
instances and counted the pick and the drop (a-parcel-astray-is-a-want-of-its-own): the joint want's
estimate is the desire's sum, ten at the root and the plan's own cost, so every interleaving of the
two five-step chains stands at ten on the frontier and is opened in turn, and the 80 candidates beyond
the 148 worlds weighed are interleavings that reached a world already made. The default budget of 128
cuts it short, so the world's tests state 256 and the corridor's 512. Twelve times the pass, for a
plan that is optimal for both parcels by construction where two plans apart could only be optimal
each; the pass still ends inside a cadence.

**Disjoint grids pay nothing but the reach.** The aversion over what the vans can reach yields no row,
the parcels stay two wants, and every count is the tree before's. The gap of 60 ms on that pose is
the reach and the noise around it: the read itself — the delete-free closure over the courier's three
constructs, seven rounds, and the aversion and the preconditions asked over it — is 17 ms a pass on
the shipped 4x4 (median of five, 12.9 to 20.8), and a holder with no aversion pays one query.

**The corridor's coupled search visits 18 worlds holding two vans on one cell and refuses none**,
across five cells, since the bound (#902) is not built; the ten-step plan it finds happens to walk
the vans past `c2_1` one at a time, which the test pins as what is true and not as a promise. And
the pose that found the product's ceiling: both vans on one cell with their parcels where they stand
is a joint delivery of thirteen steps that neither 128 nor 512 finds — 32 s at 512 — which is the
trigger the record's first seam names, pinned `Exhausted` beside the aversion's own one-step want.

# The dispatcher: the invariant weighed in every possible world, and the worlds it refuses (2026-10-05, #902)

*Superseded the next day: the aversion became a `planning:Constraint` and a refused world an
impossible one (the section after this). The figures below are the bound's as measured on the
desire's form, and `planning:refused` is retired; they are kept because the section after compares
to them.* The bound [one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md)
decided: `Planner.expand` weighs each state [invariant](/domain/planning/constraint.md) of the holder
whose select reads a predicate the scope's actions write in every possible world it weighs a want in,
and a world whose weighing carries a violation row its parent's lacks is refused — `planning:refused`
on the want's weighing in place of its verdict, `planning:open` and `planning:met` taken back, so the
frontier's and the plan's reads pass it by unfiltered. Measured on the development container, `origin/main` at `3cd44687`
exported to the scratchpad and the tree with the bound alternated per round in one session, five rounds,
one pass of the Planner over the booted world as `world/dispatcher/tests/test_dispatcher.py` builds it;
candidates and weighings as the sections above count them, refusals the weighings carrying
`planning:refused`, two-van worlds every possible world holding two vans on a cell, whether or not the
search ever opened it. The counts did not move between rounds on either tree.

| pose | tree | budget | candidates | weighings per want | refused | two-van worlds | plan | pass, median of five (min) |
|---|---|---|---|---|---|---|---|---|
| apart, as shipped | before | 256 | 228 | 148 | - | 0 | one of ten steps | 2406 ms (2304) |
| apart, as shipped | after | 256 | 228 | 148, and the aversion in 148 | 0 | 0 | the same | 2786 ms (2599) |
| the corridor | before | 512 | 296 | 216 | - | 18, none refused | one of ten steps | 5348 ms (4556) |
| the corridor | after | 512 | 286 | 210, and the aversion in 210 | 13 | 16, 13 refused and 3 passed over by hash; none opened | the same, walked with two vans on no cell | 5378 ms (4885) |
| van B parked on `c2_1`, parcel A owed at `c3_1` from `c1_1` | before | 128 | 66 | 58 | - | 11, judged by nobody | five steps THROUGH van B | 353 ms (310) |
| the same | after | 128 | 56 | 49, and the aversion in 49 | 7 | 8, 7 refused; none opened | five steps BY VAN B, which stands beside the parcel; van A never moves | 466 ms (316) |
| parcel A aboard van A at `c1_1`, van B parked on `c2_1` | before | 128 | 26 | 24 | - | 5 | three steps through van B | 113 ms (93) |
| the same | after | 128 | 66 | 52, and the aversion in 52 | 5 | 8, 5 refused; none opened | four steps: van B aside, van A through — the route round is five | 341 ms (307) |
| both vans on `c0_0` | before | 128 | 4 and 128 | 4 and 70 | - | 16 | the aversion's one-step drive; the joint `Exhausted` | 693 ms (600) |
| both vans on `c0_0` | after | 128 | 4 and 128 | 4 and 75, and the aversion in 75 | 0 and 7 | 14 | the same | 865 ms (760) |
| both vans on `c0_0` | after | 512 | 4 and 512 | 4 and 263 | 0 and 11 | 24 | the joint still `Exhausted`, 39 s | one run |
| the vans on disjoint grids | before | 128 | 27 and 27 | 23 and 23 | - | 0 | two of five steps | 270 ms (169) |
| the vans on disjoint grids | after | 128 | 27 and 27 | 23 and 23, and the aversion in 42 | 0 | 0 | the same | 297 ms (209) |

**What a world costs.** `Planner._bound` timed over one pass, the aversion's weighing and the two
row reads inside it: 0.70 ms a candidate on the corridor (199 ms of a 4461 ms pass, 286 calls) and
0.72 ms on the parked van (40 ms of 293, 56 calls) — against the 0.56 ms the record measured for the
weighing alone, the rest being the child's rows read once and the parent's read once per pass. The
invariant's select is compiled once per pass as a want's met-test is (`weigh` memoises it under
`("select", desire)`), and the invariants of a scope are found once per pass. A holder with no
invariant pays the one query that finds none, two round trips: the search bench
(`agent/planning/tests/test_bench.py`) alternated twice read 60, 154 and 162 ms before against 56, 149
and 160 after, then 42, 159 and 150 against 46, 129 and 170 — two disks, three disks, the courier's
corner, 220 queries a pass where 218 were — and the pass bench (`world/greenhouse/tests/test_bench.py`)
read its search lap 62, 29, 90 and 29 ms before against 62, 30, 94 and 23 after, then 51, 23, 79 and 29
against 55, 29, 91 and 27, its four cases in order, five quads more for the term's declaration; both
inside the drift the other laps show. **And one representation was refused on this bench:** the
refusal first kept the want's verdict and filtered the frontier's achiever read and the plan's with
`FILTER NOT EXISTS { ?y planning:refused ?by }`, and the search bench read 58, 150 and 176 against
main's 44, 112 and 133, a quarter of every pass for holders with no invariant at all; with the filter
struck the same tree read 45, 124 and 135. So the refusal replaces the verdict, and the reads carry no
filter.

**What the bound did.** On the corridor it refused the thirteen worlds in which a van is driven onto
the other's cell and opened none of the sixteen that hold two vans — the other three were forked and
passed over by hash as repeats of a refused one — and the plan is the one found before, since the
colliding interleavings were never on the shortest path: ten candidates fewer, no step changed, and
the walk now shares no cell by promise. On the shipped pose it refused nothing, because no world of
it collides, so 228 stands and the default budget of 128 still does not suffice; neither did the
corridor's 286 fall under 256, so the tests' budgets stand. **The parked van was the surprise.** The
record expected the seven-step route round; the one mind holding both vans found better twice over —
with the parcel on the ground beside van B it delivers with van B, five steps and van A never moves,
and with the parcel already aboard van A it moves van B aside first and drives through, four steps.
The route round is what a mind holding one van finds. There the estimate reads three and the plan
costs four: admissible, loose by the step the invariant costs and the parcel does not owe, which the
estimate test pins as not tight for that pose alone. **The together pose** still mints the aversion's
want and finds its one-step drive in 4 weighings, since an invariant already unmet in the root bounds
nothing a repair does; the joint want is still `Exhausted` at 128 and at 512, 39 seconds, so the
product's seam stands as written. **Disjoint grids** pay the aversion's weighing in all 42 worlds
though none can hold two vans: the bound reads the invariant's footprint by predicate, and `at` is
the drive's, where the reach would have told it nothing collides — the record's seam.

# The dispatcher: the constraint a kind of its own, and the worlds it makes impossible (2026-10-06)

The rework of the section above, decided with the sovereign: a [constraint](/domain/planning/constraint.md)
is a check that a world is POSSIBLE and a met-test that it is DESIRED, so the dispatcher's two-vans
rule is a `planning:Constraint` and no desire (`world/dispatcher/constraints.ttl`), `Planner.expand`
weighs it in every possible world it weighs a want in, and a world where it yields a row is
`planning:impossible` on its own row with the want's weighing of it bare — no parent compared, no
repair — while a present that violates it is a contradiction the pass says and `orexis-onboard`
refuses, and mints nothing. Measured on the development container, the tree before — `10f32c49`, the
courier's band, which is the section above's code — exported to the scratchpad and this tree
alternated per round in one session, five rounds, one pass of the Planner over the booted world as
`world/dispatcher/tests/test_dispatcher.py` builds it; candidates, weighings and two-van worlds as the
sections above count them, impossible the possible worlds marked. The counts did not move between
rounds on either tree.

| pose | tree | budget | candidates | weighings per want | impossible | two-van worlds | plan | pass, median of five (min) |
|---|---|---|---|---|---|---|---|---|
| apart, as shipped | before | 256 | 228 | 148, and the aversion in 148 | 0 refused | 0 | one of ten steps | 3110 ms (2955) |
| apart, as shipped | after | 256 | 228 | 148, and the constraint in 148 | 0 | 0 | the same | 3317 ms (3132) |
| the corridor | before | 512 | 286 | 210, and the aversion in 210 | 13 refused | 16 | one of ten steps, sharing no cell | 6152 ms (6113) |
| the corridor | after | 512 | 286 | 210, and the constraint in 210 | 13 | 16, 13 impossible and 3 passed over by hash; none opened | the same | 6695 ms (6188) |
| van B parked on `c2_1` | before | 128 | 56 | 49, and the aversion in 49 | 7 refused | 8 | five steps BY VAN B | 373 ms (364) |
| the same | after | 128 | 56 | 49, and the constraint in 49 | 7 | 8; none opened | the same | 434 ms (389) |
| parcel A aboard van A, van B parked | before | 128 | 66 | 52, and the aversion in 52 | 5 refused | 8 | four steps: B aside, A through | 402 ms (387) |
| the same | after | 128 | 66 | 52, and the constraint in 52 | 5 | 8; none opened | the same | 435 ms (372) |
| both vans on `c0_0` | before | 128 | 4 and 128 | 4 and 75, and the aversion in 75 | 7 refused | 14 | the aversion's one-step drive; the joint `Exhausted` | 966 ms (837) |
| both vans on `c0_0` | after | 128 | 128 | 75, and the constraint in 75 | 7 | 14 | NO want from the constraint; the present a contradiction, said; the joint `Exhausted` | 916 ms (891) |
| the vans on disjoint grids | before | 128 | 27 and 27 | 23 and 23, and the aversion in 42 | 0 | 0 | two of five steps | 378 ms (362) |
| the vans on disjoint grids | after | 128 | 27 and 27 | 23 and 23, and the constraint in 42 | 0 | 0 | the same | 357 ms (343) |

**Every count held, and one pose changed meaning.** On every pose where the bound refused a world,
impossibility marks the same world: on the dispatcher's grid no world the search makes keeps a
violation the present had, so "never newly enter" and "impossible" name the same thirteen worlds on
the corridor, seven on the parked van, five with the parcel aboard. The together pose is where the
two differ: the aversion's one-step want and its 4 weighings are gone, the pass warns `the present
violates no_cell_holds_two_vans, a constraint of this world, and nothing repairs it: (van_a, 0, c0_0),
(van_b, 0, c0_0)`, `reading.contradicted` answers the same row to `orexis-onboard`, and the joint
want's search still marks the seven worlds that part the vans and bring them together again — those
are worlds the search made, and the present's own violation is not one. The timings lean a few
percent slower on the searched poses and faster on two, all inside the drift this machine shows
between rounds of one tree (the shipped pose's five base passes ran 2955 to 3447 ms). What was added
per candidate is one `OPTIONAL` in `weigh`'s `_ABOUT_Q`, reading the world's mark, and one in the
planner's `_REACHED_Q`; what was removed is the parent's rows read once per pass per world. The
search bench (`agent/planning/tests/test_bench.py`), a holder with no constraint, alternated twice,
read 61, 182 and 183 ms before against 76, 198 and 175 after, then 74, 167 and 177 against 79, 175
and 198 — two disks, three disks, the courier's corner, 225, 475 and 548 queries a pass on both
trees, so no query was added to a holder with none — and the greenhouse pass bench
(`world/greenhouse/tests/test_bench.py`) read its search lap 78, 28, 108 and 35 ms before against 68,
28, 87 and 33 after, then 61, 51, 108 and 31 against 57, 33, 88 and 30, its four cases in order,
seven quads more for the three terms declared. **What stands from the section above:** the mark takes
the verdict back rather than filtering the frontier's read, since the filter cost a quarter of every
pass; the marked world and its weighings are kept, not forgotten; and the parked van is still
delivered by van B, or van B moved aside, with the estimate loose by the step the constraint costs.

# The courier's drives take a stretch (2026-10-05, #901)

`domains/courier/actions.ttl` declares `planning:landsAfter` — a drive lands between 30 and 60
seconds after it is taken, a pick and a drop at once — where it declared nothing and every world and
step of a delivery stood at the pass's one instant
([a-landing-is-a-band-and-a-world-holds-over-a-period](/decisions/a-landing-is-a-band-and-a-world-holds-over-a-period.md)).
Measured on the development container, the base (`7009c7a7`) and the tree with the band alternated
twice in one session by switching this worktree's HEAD, one pass of the Planner over the booted world
at the budget its tests state, medians of five for the bench and of three for a world; the bench's
`courier_corner` fixture carries the band too, since the runbook holds it to the domain's text.

| case | tree | candidates | worlds, distinct hashes | distinct periods | queries a pass | pass, median (min) |
|---|---|---|---|---|---|---|
| `courier_corner`, budget 128 | base | 45 | — | — | 484 | 164 ms (138), then 196 (168) |
| `courier_corner` | band | 45 | — | — | 548 | 182 ms (174), then 159 (135) |
| `world/courier`, budget 128 | base | 45 | 45, 27 | 1 | — | 207 ms (148), then 198 (181) |
| `world/courier` | band | 45 | 45, 27 | 7 | — | 187 ms (183), then 142 (137) |
| the dispatcher, apart, budget 256 | base | 228 | 228, 149 | 1 | — | 2436 ms (2382), then 2813 (2551) |
| the dispatcher, apart | band | 228 | 228, 149 | 7 | — | 2590 ms (2508), then 2517 (2420) |

**The band shifts instants and not the frontier's order.** Every count is the base's: 45 and 228
candidates, the same steps, and the digest of every world's `orexis:hash` sorted is the same string
on both trees for both worlds (`7760df54…` and `8940894b…`), which is what #907 promised — a world is
hashed within what is read and its period is on its row, so a landing moved no world. What the band
costs is 64 queries on the corner's 484: the `landsAfter` select asked once per candidate taken,
the ground at each distinct landing instant and the graph list per distinct period, each remembered
per instant; the times are inside the session's drift both ways. The hanoi cases read one query more
(224 to 225, 474 to 475), which is the derivation's and not the band's: `_named` reads what stands
under a desire once more, for the covering rule below.

**What the plan carries now**, pinned in `world/dispatcher/tests/test_dispatcher.py`: each step
opens where the one before it lands, the six drives of the joint plan land at six distinct instants,
the last step lands between three and six minutes after the root, every possible world holds over the
period its step's two ends say, and each committed step is believed from its opening to its latest
landing plus the patience — a drive's `landsWithinS` 30 and its window two minutes and more, where
every window was the patience alone.

**And a walk is passes.** A fictive drive writes its effect the instant it is taken, but the executor
looks for it from the step's `landsAt`, half a minute on, so a plan of drives is walked a drive a pass
and the worlds' tests tick their clocks — the dispatcher's by the least between passes, the courier's
a second a read, the tower's five. That walk showed what one pass had hidden: midway through the joint
plan the desire read unmet for the parcel still astray alone, and the derivation minted a want for it
under a name of its own beside the coupled want still walking, whose second plan drove the same van
down the same cells (12 acts for 10 steps, measured). A cluster a standing want is already about is
that want's now, and the shipped dispatcher's walk is one intention, ten acts, as before.

# Before Agent 0.2.0

The 0.1.0 planner's tracked table, where its time went, and the criteria a Rust SHACL judge
would have had to meet were measured on a different search over a different store and bind
nothing here. They are in this runbook as it stood at `3e1ba134`.
