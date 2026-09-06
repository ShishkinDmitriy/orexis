---
type: Runbook
title: Measure the search
description: >-
  How to time and profile the planner on world/hanoi, the tracked measurements, and the
  criteria a faster SHACL engine has to meet before it may judge. Numbers are commits, not
  impressions: every row names what ran and where.
---

# Why hanoi is the bench

`world/hanoi` is the measuring stick because it is all search: no bus, no sensors, no
containers — a plain agent, one desire, one action, and the plan is the whole cost. A change
that moves these numbers moved the planner, not the weather. See
[the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md).

# How to measure

```bash
pytest tests/test_hanoi.py -n0 -q --durations=5        # wall, per test
python -m cProfile -o /tmp/hanoi.prof -m pytest \
    tests/test_hanoi.py::test_three_disks_solve_in_exactly_seven_moves -n0 -q
python -c "import pstats; pstats.Stats('/tmp/hanoi.prof').sort_stats('cumulative')\
    .print_stats('orexis/(packages|agent|tests)/', 14)"
```

Wall times, not profiled times: cProfile roughly doubles everything, so the profile is for
SHARES and the `--durations` run is for the row below. One machine, the bench, stated per
row — a number without its machine is an impression.

# Tracked

| date | commit | 3 disks (depth 8) | 2 disks | notes |
|---|---|---|---|---|
| 2026-08-31 | `718274e` | 5.8 s | 1.9 s | six ground actions; first measurement |
| 2026-09-01 | `13876fc` | 5.71 s | 2.65 s | ONE Move action — one action costs nothing |
| 2026-09-01 | `the-judge-speaks-rust` | 6.19 s | 2.55 s | rudof judge, Turtle border |
| 2026-09-01 | `the-judge-speaks-rust` | **5.52 s** | 2.17 s | the border speaks N-Triples — rdflib's Turtle WRITER was a third of the judge's cost |
| 2026-09-01 | `a-node-holds-one-world` | **2.03 s** | 1.67 s | the per-node rdflib copy is gone (#481) — 198,144 `Graph.add` calls became 23,282 |
| 2026-09-01 | `best-first-by-what-is-left-to-spend` | 1.77 s | 1.51 s | best-first on `cost + estimate` (#492): hanoi 56 forks to 50, the courier's corner delivery 198 to 78 |
| 2026-09-05 | `the-law-carve-reads-the-data-alone` | 2.32 s (main 2.17 s, same run) | — | the pass's flatten leaves the T-Box out except its node shapes (#484): `_beliefs()` 140 ms / 3,172 triples to 45 ms / 591 on `world/simulation`, `_begin` 237 to 115 ms; hanoi's one pass moves inside noise, a plant's tick pays the whole saving |
| 2026-09-06 | `leave-the-fork-loop-free-of-rdflib` | — | — | the fork loop touches no rdflib graph (#547): the held shapes carved once per pass, a shape's target resolved in the imaginarium (the wants copied in beside the beliefs — a desire shape TARGETS a want), rudof's report read as N-Triples by pyoxigraph, and the data read into rudof once per verdict pair; `conforms_at` 380–430 ms became 230–240 ms on `world/simulation`, `_begin` 126 to 142 ms median (the carve moved in, once). Per verdict the floor is now rudof's own: `read_data` ~90 ms, `read_shacl` ~50 ms, validate ~60 ms |
| 2026-09-05 | `the-legality-check-reads-the-border-text` | — | — | the winner's legality is judged on the border text the law already reads (#485): parse 150 ms + `conforms` 510–970 ms became `conforms_at` 380–430 ms on `world/simulation`, the rdflib round trip gone; what is left is two rudof verdicts over 3,855 triples |

# Where the time goes (profiled at `13876fc`)

That reading is now history, and it is kept because the shape of it recurs: **~70% of the
solve was `effects.applied`**, copying the entire ~2,300-triple world into a fresh rdflib graph
per candidate to express a step that changed four triples — O(world) where the work is
O(diff) — while all 1,237 SPARQL queries cost 0.4 s. The copy existed to feed a judge that
read rdflib. Both are gone (#481,
[a-node-holds-one-world](/decisions/a-node-holds-one-world.md)).

Profiled at `a-node-holds-one-world`, the same solve:

| | |
|---|---|
| pyoxigraph — 1,280 SPARQL queries and every world dump | 14% |
| rudof — four verdicts, most of it its reader's fixed floor | 8% |
| rdflib — down from 55%, and 23,282 `Graph.add` calls from 198,144 | 33% |
| **our own planner and kernel Python** | **6%** |

What is left of rdflib is per-PASS rather than per-node: parsing the wants, and the one world
`_offer` flattens to check legality. Boot (`runtime.Agent` + `validate_agent`) is ~1.5 s and
outside the search.

**The planner's own logic has never been the cost** — 4–6% across every profile taken here.
A faster language for it would buy that much and no more; what bought 3× twice over was
moving data less.

The two levers, in order: judge through a faster engine (below), and stop paying the
per-node rdflib copy — a node's flat world already exists in the imaginarium, so the rdflib
view could be derived lazily at the one boundary that needs it (#481).

# Why a Rust engine is not automatically faster

Worth keeping, because the first swap made the bench SLOWER (5.71 s → 6.19 s) with an engine
that is genuinely quicker at the thing it does. Measured per verdict on 2,400 triples:

| | |
|---|---|
| rudof's validation proper | **16 ms** — against pySHACL's ~100 ms for the same work |
| rudof's `read_data` | **67 ms for TWO triples**, a fixed floor paid on every call — per READ, not per instance: re-measured 2026-09-06 at 73–89 ms whether the world is two triples or 3,500, and the same again after `reset_data` |
| rdflib writing Turtle at the border | 86 ms — its writer groups by subject and hunts prefixes |
| rdflib writing N-Triples instead | **12 ms**, four times the bytes and nobody reads them |

So the engine was never the cost: the BORDER was, plus a fixed floor inside the reader. Two
lessons generalise past this repo. **A faster engine behind a serialization boundary is a
slower system until the boundary is cheaper than the win** — and the cheapest fix was choosing
the dumber format, because the expensive half is the WRITER, not the parser. **And a fixed
per-call floor decides everything at small volume**: our worlds are ~2,300 triples, where 67 ms
is most of a verdict.

In our pattern — the data arrives as an rdflib graph and must cross — the two judges cross
over around **5,000 triples**:

| triples | pySHACL | rudof (N-Triples border) | |
|---|---|---|---|
| 300 | 16 ms | 83 ms | pySHACL 5.2× |
| 2,400 | 124 ms | 130 ms | even |
| 9,000 | 478 ms | 276 ms | rudof 1.7× |
| 60,000 | 3.7 s | 1.9 s | rudof 2.0× |

We sit just below the crossover and still come out ahead end-to-end, because a solve pays the
border once per `conforms` rather than once per shape. Closing #481 — crossing straight from
the imaginarium's pyoxigraph store, whose Rust writer replaces rdflib's — moves the whole curve
and is where the remaining win is.

# What the search costs, and the one thing that breaks it

A pass is deep and narrow: the menu is 2–3 rows per node on hanoi and ONE in `world/simulation`,
because a precondition query only yields a row whose premises hold. So the levers that pay are
about depth, not width.

**Cost bound**, landed: `orexis:costs` is asked before a candidate is simulated, and one already
dearer than the cheapest plan in hand is dropped unsimulated and unforked. Sound rather than
heuristic — cost is non-negative and a path sums it, so no descendant can beat the bound.
Measured on 3 disks: 76 forks to 56, depth 8 to 7, 20 candidates refused, 2.05 s to 1.69 s.
Strictly dearer, never `>=`: a free action lets a descendant tie, and an achiever tying on cost
still wins on urgency.

**Best-first by `cost + estimate`**, landed (#492), and what it replaced is worth keeping because
it looked like it should have worked. `orexis:estimates` arrived with `cost + estimate > bound`
pruning, sound and measured to prune NOTHING: the search expanded breadth-first by layer, so
the first achiever arrived in the last layer and a bound that arrives last has nothing left to
refuse. Sorting within a layer could not help — the layer is expanded whatever the order. One
heap keyed on `cost + estimate` (urgency, then cost, breaking ties) with early termination when
the head's key passes the bound is the whole change, and a met want keeps the old
insertion order because its answer IS the first keeper. Forks per solve, same plans:

| | breadth-first | best-first |
|---|---|---|
| courier, corner delivery, optimal 8, depth 8 | 198 | **78** |
| courier, near delivery, optimal 5, depth 8 | 63 | **34** |
| hanoi, 3 disks, no estimate, depth 8 | 56 | 56 — plain cost is uniform-cost search, which is breadth-first for unit moves |
| hanoi, 3 disks, counting disks astray, depth 8 | 56 | **50** — a weak floor, since the optimal path moves disks away from C |

**A shape want is judged by its compiled select** (#497): the judge's reader floors at ~67 ms
per call and a plant pass judged every candidate world with it; the select the kernel compiles
from the shape runs on the store's own engine in about a millisecond. Measured on the fern, dry,
one pass at the default budget: **0.41 s with the judge per node, 0.21 s compiled**. Hanoi and
the courier are unchanged, since their patterns were selects already — now derived rather than
written. The judge is reached once per pass, for the winner's legality.

**The ceiling is a budget of worlds** (#494): `deliberation:budgetWorlds` on the agent, 32 by the
engine's default, 64 in `world/hanoi` and 128 in `world/courier`. Multiply by the fork cost for
the mutable slice above to size one in seconds. A spent budget answers with the best so far.

A world is claimed by the first path to reach it, and best-first can reach one by a dearer path
first, so a world reached strictly cheaper is reopened. Measured: it never happens in either
domain — unit costs and an estimate that moves by at most one per step give two paths to one
world equal keys, and the cheaper pops first — so the guard has no witness here and is kept
for the domain whose costs are real numbers.

**The thing that breaks all of it: a free action from another domain.** Added ONE to `world/hanoi`
as data — a knob flipping between two positions, no cost, genuinely changing state:

| | forks | refused by the bound | wall |
|---|---|---|---|
| hanoi alone | 56 | 20 | 2.26 s |
| + one free foreign action | **157** | **20** | 3.77 s |

2.8x from one lever, ~2^k from k of them, and every defence misses it: the bound is blind to a
free action, cycle detection cannot fold a world that genuinely changed, and the want scoping in
`_candidates` only filters rows whose `available` binds `?want` — which a foreign package need
not, and which the hanoi want skips entirely for want of an `orexis:about`. The plan stays
CORRECT; only the cost explodes, which is why nothing catches it.

That was [#488](https://github.com/ShishkinDmitriy/orexis/issues/488), closed by
[relevance](/domain/relevance.md): what the want reads off its shape, what each action writes
and reads off its texts, closed backward. Re-measured with the budget in place of depth, which
changes what the knob costs — no longer a slower solve but a SPENT budget and no solution:

| | relevance off | relevance on |
|---|---|---|
| hanoi, 3 disks + the knob, budget 64 | 64 forks, EXHAUSTED at 3 moves | **50 forks, solved in 7** |
| courier, corner delivery + two of hanoi's disks in the world, budget 128 | 128 forks, EXHAUSTED at 6 steps | **78 forks, delivered in 8** |

The same forks as with no foreign lever at all, in both. Two domains share an agent now, which
is the half of the plug-in claim that was owed.

# The number that decides the search's shape: the mutable slice

A search node holds the FULL mutable slice of its world — its readings — not a diff, so
expansion is O(state) per node however small the step was. Measure it before assuming a world
is cheap to search:

```bash
python -c "
import sys; sys.path.insert(0,'tests')
from conftest import genesis_store
from orexis_agent_progression.ontology import STATE_GRAPH
st = genesis_store(world='<world>')
print(len(st.dump_nt(STATE_GRAPH).splitlines()), 'triples in the mutable slice')"
```

Measured cost of forking one node as that slice grows, the diff held at one triple:

| mutable slice | fork | + dump, if the world is judged | × 78 nodes, unjudged |
|---|---|---|---|
| 1,000 | 3.8 ms | 4.5 ms | 0.30 s |
| 10,000 | 45 ms | 57 ms | 3.5 s |
| 50,000 | 263 ms | 321 ms | 21 s |

Linear, paid once per node. The shipped worlds sit at 3–5 triples, where it rounds to nothing.
Past roughly a thousand the per-node copy stops being free, and past ten thousand it IS the
search; the design to reach for there is an overlay, whose price is stated in
[a-node-holds-one-world](/decisions/a-node-holds-one-world.md).

**Two things already keep that number down**, and a third looked obvious and was wrong:

- the fork is the ENGINE's copy, not a Python loop over quads — a quarter off, all of it
  interpreter overhead per quad;
- a world is written out only if something JUDGES it. A 3-disk solve forks 76 worlds and reads
  one, because a want met by a pattern is judged by the store at the node's graph and never
  needs text;
- **not** skipping the fork for a world already seen, which measured 49 of those 76. A
  cycle-discarded step still has its urgency scored and its met-test run, both of which read
  its world — deliberately, since a look nets to nothing in canonical form, so the step that
  repairs a freshness want is ALWAYS the non-novel one. Pruning before the met-test would make
  freshness unplannable, and reusing a graph by signature would conflate worlds differing only
  in a timestamp, which is the same bug from the other side.

# The judge in Rust: criteria before adoption

The engine under everything else is already Rust (pyoxigraph). The judge is not:
[pySHACL](https://github.com/RDFLib/pySHACL) only speaks rdflib, which is why rdflib
survives in the kernel at all. Candidate: [rudof](https://github.com/rudof-project/rudof)
(`pyrudof`) — alive by measurement (8 releases in Aug 2026, two on 2026-08-31; PyPI in
lockstep).

Probed at `pyrudof 0.3.16`, every SHACL feature our shapes use, one expected violation each:

- **Handles**: all Core we use — counts, ranges, `sh:datatype`, `sh:class`, `sh:nodeKind`,
  `sh:hasValue`, `sh:in`, `sh:lessThanOrEquals`, `sh:not`/`sh:or`/`sh:xone`/`sh:node`,
  `sh:inversePath`, qualified value shapes, `sh:targetNode`/`Class`/`SubjectsOf`/`ObjectsOf` —
  **and `sh:SPARQLConstraint`**, its own tracker notwithstanding.
- **Gap 1 — `sh:SPARQLTarget` binds NOTHING, silently** (we hold 21). The empty-result trap
  in a new coat: a shapes family would simply stop applying, and no test would go red on the
  engine's account. Closed on our side: the seam resolves SPARQL targets itself, on our own
  engine, and hands the judge explicit `sh:targetNode`s.
- **Gap 2 — an authored `sh:message` is sometimes overwritten** by the engine's own prose (a
  qualified max-count reports its arithmetic where the shape named the plant and the edge).
  Closed on our side: the door restores the author's message, correlating by `sh:sourceShape`.
- **Not a gap, though the first measurement said so — `sh:severity`.** rudof honours it in
  exactly pySHACL's two places: down on the property shape for a declarative constraint, up
  on the node shape for a `sh:sparql` one. A split apparatus was built for this and deleted.

Adoption is legitimate exactly when the full suite and every world's `orexis-validate` pass
with the seam in place — the same gate every other change answers to. **A row below says so**:
the judge is rudof, behind `packages/orexis-agent-deliberation/judge.py`, both gaps closed on
our side of the door — see [the-judge-speaks-rust](/decisions/the-judge-speaks-rust.md).
pySHACL remains the reference the inference-parity gate holds the closure against.

| date | engine | probe / result |
|---|---|---|
| 2026-09-01 | pyrudof 0.3.16 | feature probe as above; 2.5k-triple parse+validate ×10: rudof 1.18 s, pySHACL 2.60 s |
| 2026-09-01 | pyrudof 0.3.16 | ADOPTED. Blank focus nodes break rudof's VALUES pre-binding — skolemize at the door, but ONLY the data and the constraint carriers: naming a property path's blank nodes breaks the path. Border crossed per verdict at first (7.95 s); serialize-once + caches: 6.19 s |
