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

# Before Agent 0.2.0

The 0.1.0 planner's tracked table, where its time went, and the criteria a Rust SHACL judge
would have had to meet were measured on a different search over a different store and bind
nothing here. They are in this runbook as it stood at `3e1ba134`.
