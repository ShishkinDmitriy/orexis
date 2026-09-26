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

# Before Agent 0.2.0

The 0.1.0 planner's tracked table, where its time went, and the criteria a Rust SHACL judge
would have had to meet were measured on a different search over a different store and bind
nothing here. They are in this runbook as it stood at `3e1ba134`.
