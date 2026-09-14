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
| 2026-09-08 | `a-greenhouse-wants-two-things-at-once` | — | — | `world/greenhouse` (#566), with `climate:` beside `water:` as the domain's second vocabulary — a heater and a vent: one bed, one want about two properties, a dose and a heating. A cold dry bed plans both in about 1.8 s, spending its whole 128-world budget — neither lever states a cost, so no bound prunes and the pass explores until the budget stops it. THE KNOB: with `climate:driesTheSoil` the plan REORDERS itself, heating before dosing, because warming writes the soil reading the dosing rule reads and a dose warmed afterwards is undone; nothing declares the order. What the knob does NOT change is the scope count — one in both regimes, since both readings carry the same predicates, which is the predicate-level limit #565 measured. THE VENT is the first effect whose outcome the world decides: the same act reaches `inside` at 21 degrees outside, `below` at 5 and `above` at 30, read off the bed's own band definitions, and with the heater gone it is planned onto a warm afternoon and refused onto a cold night |
| 2026-09-11 | `a-graph-holds-during-a-stretch` | — | — | a graph says which stretch it speaks for and the door drops what is outside its range (`a-graph-holds-during-a-stretch`, #589's first half). The filter is where the clock is read and the only place: 0.9 us per `public_graphs()` call with no range stated — the fast path every shipped world takes, since none states one — and 1.9 us with one, against the milliseconds of the query it precedes. The TABLE is remembered rather than a filtered list, because which graphs speak for now depends on when it is asked and the table does not, so a memo keyed by an instant would miss on every call |
| 2026-09-10 | `a-node-is-a-world-and-an-instant` | 0.50 s / 50 forks (unchanged) | 0.74 s / 14 forks (unchanged) | identity is world-and-GROUND (#587): a node's key is its diff and which of the world's own branches it sits under, which is the present for every node of every pass until something predicts — so the key is the diff it always was, and every shipped world is unchanged in forks and steps. THE MEASUREMENT IS WHY IT IS NOT THE NODE'S TIME, which is what the issue asked and what this carried for a day. Keying on the path's summed `orexis:landsAfter` also changed nothing anywhere — hanoi 14 and 50, the courier 71, the greenhouse 128 in both knob regimes, both plants 2 — because doubling back inside a budget needs an action that declares a landing AND returns to a pose, and no shipped world has one. Where one was declared it cost the grip: a hanoi move given a minute took two disks from 14 forks to 17 and three from 50 to the whole 128-world budget, still three and seven moves, and at that world's own 64 the timed solve answered `exhausted` at 64 forks where it used to solve. It cost a shipped answer too: a market host owing water it does not hold planned a serve from a barrel too low instead of the refill, a dry serve predicting nothing having stopped colliding with the world it was predicted from. A later world differs because something the world DOES happened in between, which is a prediction and not a clock — so no grain is guessed, and time reaches identity through the ground (#589, #592) |
| 2026-09-08 | `a-scope-is-measured-before-it-is-a-mechanism` | — | — | scopes from relevance's tables (#565 item 1): predicates joined wherever one action or derivation reads or writes both. Measured on every shipped world — loner, simulation, courier, hanoi — ONE scope of about ninety predicates, with the derivations counted or the actions taken alone, and every want of every shipped agent inside it. So one cone per scope has nothing to split and is not built. The actions alone already join the market's plumbing to sensing's readings, because every shipped effect predicts a reading of the same shape; and a scope of PREDICATES cannot separate two vans, which needs a variable, a subject and a predicate together |
| 2026-09-08 | `an-effect-declares-the-band-it-reaches` | 1.39 s | — | the effect declares the band and progression sizes the act (#579): the dosing, acquiring and serving rules state what the reading BECOMES and no number, `orexis:size` is gone, the keeper holds the world to the class and the region want's met-test asks `sh:class`. Plant pass 1.13 s over 2 forks against 1.08 s over 4 before — one step where there were two, which is the ruling's cost: two doses each too small to cross a boundary are found by re-planning. Membership moved out of SPARQL and into the store: as one query it cost 300 ms a call however narrowed, and a pass forks tens of worlds, so the definitions are read once and evaluated against a node's triples. Entailment forgets nothing, since a type triple in one graph moves no memo — forgetting re-read the definitions 25 times a pass, 140 ms each |
| 2026-09-07 | `a-reading-is-what-the-domain-says-it-is` | — | — | a reading is what the domain says it is (#576): sensing declares five band families, genesis mints a member per (subject, property) with a range as an OWL intersection, and `Store.entail` asserts membership when a reading is written, when a fork adds one and when a volume boots — a generic rule over `owl:intersectionOf`, `owl:hasValue` and `owl:withRestrictions` facets, 2.6 ms on a toy of three classes. The match, a premise and a remembered plan's key read the band; the number still moves a world (#579). Plant pass 1.08 s / 4 forks with the entailment per fork (1.0 s before, same load); hanoi 7 / 50 and the courier 8 / 78 unchanged. The kernel partition of #573 is deleted |
| 2026-09-07 | `a-readings-identity-is-its-cell` | — | — | a reading is matched by its cell (#573): thresholds read off the shapes that bound a reading and the selects' constants — moisture in the loner world has four, the butt's level none, being compared against a variable. Tried first as the identity of every canonical fact and refused by the suite: a dose that moves the pot within its cell is progress and steering inside the region is work, so the cone's diffs stay by number and the cell applies at the match and in premises. The plant drift test flipped: a hundredth off the prediction resumes, a threshold crossed does not. A match by cell that is not exact re-roots at the node, re-scores it from the present and drops what was imagined beneath it — those worlds were computed from the number the node predicted, and a dose from 0.54 is not a dose from 0.50; an exact match keeps the subtree, as a puzzle world's always is |
| 2026-09-07 | `a-surprise-is-classified` | — | — | a surprise is classified (#570): a miss completes what the last pass withheld at every kept node — its withheld rows, and every row of a node the budget stopped before expanding — before giving up; a world found that way is `withheld`, none is `exogenous`, said on the pass with the facts within the view. Refused worlds (forbidden, late, dear) are kept with their verdict, so the avoidance fixture's tempting world, entered anyway, is identified and the exit planned from it. Completion is bounded by the frontier and the withheld rows, both by the budget |
| 2026-09-14 | `the-drift-is-sensings-and-its-result-is-predictions` | — | — | #642: after a reading the simulation fern holds four predictions — the next window, an hour, five hours, a day — each a graph holding during its window with the predicted reading typed by the water drift; with a spread and a noise stated the first window at 0.47 types the in-region band and the one below, with none it types one; the door hands the prediction holding at an instant and the records never list it. The kernel still runs the same drift at forks, so every world's forks are unchanged |
| 2026-09-14 | `a-root-holds-always-and-an-outdated-graph-is-dropped` | — | — | #644: the roots authored at genesis into `graph/roots/<agent>` and projected, the rebuild running no rule; every world's plans unchanged, held by the suite. A root carries no foresight and no aim: the choir answers the foresight at derivation |
| 2026-09-13 | `the-agent-keeps-one-timeline-and-its-clock-may-run-fast` | — | — | #646: the simulation and the loner run a day in ten minutes and the agent predicted by the wall clock, so every crossing above was 144× late on the bench. One timeline now: at the simulation's pace the fern at 0.47 foresees its crossing four of its own hours out — a hundred bench seconds — and places the purchase ahead of it, with every figure in the rule unchanged (`tests/test_clock.py`). The bench figure — a stand-in and an agent paced alike over one day of the world — is still to be taken |
| 2026-09-13 | `a-plant-asks-ahead-and-a-round-is-scarcitys-allocation` | — | — | #627: the simulation fern at 0.47 (crossing 4 h, foresight 6 h), no round: the pass derives the want and plans nothing; the next reading carries the ask, wanted at the instant less the pour, once. The supplier at 3 L grants 0.5 L asked for at +3 h with no round; grants 1.5 L at +1 h, then convenes a round for 1 L at +2 h (1.5 − 1 under the floor of 1). Holding the granted claim, the fern's pass finds Acquiring from the latest start and places it there; at the instant the tender bids nothing and the presenting is placed at the window. Refused on running: Acquiring available on the want's instant alone placed the plan past the round a scarce host convenes now |
| 2026-09-13 | `a-host-predicts-the-arrivals-it-promised` | — | — | #626: the simulation supplier at 3 L, owing 1.5 L usable in an hour and 1 L in two — `market:Draining` reads the ledger and states the crossing as the second window; foreseeing 6 h the stock root derives the want, the pass at the latest start finds no city round holding then, stands at the present and plans Acquiring in 2 forks; a debt discharged moves the crossing out. A crossing may be an instant now, since a drift over dated debts knows the instant and no stretch |
| 2026-09-13 | `a-winner-receives-water-at-a-time` | — | — | #625: the simulation fern at 0.47 (crossing 4 h, foresight 6 h) with a round open 60 s: the pass at the latest start finds nothing (the round's period has ended by then), stands at the present and finds Acquiring in 2 forks; the bid goes out now with `wanted_at` = the instant less the pour; a claim with a window from +3 h places the Presenting step on the scheduler, nothing presented before it. Found on the way: a pass clocked from the reading's instant (#619) hid a round opened after the reading — the clock is now for every pass, and the reading's age is drifted once at the root |
| 2026-09-12 | `a-round-is-a-graph-holding-during-its-period` | — | — | #620 measured, then built: the simulation fern at 0.47 (crossing 4 h, foresight 6 h). No round open → nothing on the projected root's menu; a round open 60 s → the projected root 3.75 h out still saw the row (no period) and PLACED Acquiring into a round closing in 60 s; a root at now → Acquiring now, met at the instant. With the round as a graph holding from the offer to its close, the future root does not see it, and the door — `Store.query_at`, the rules' door for selects, taken by the afforder and the urgency choir at the node's instant — decides for every reader at once |
| 2026-09-12 | `a-drift-toward-the-surroundings-is-one-link-and-no-physics` | — | — | a bed's air drifts toward what surrounds it (#617, #619's second half): `world/greenhouse` states one `climate:Diffusion` node for its air temperature toward the outside at one degree an hour and plans EXACTLY as before — 128 forks in both regimes, dose-then-heat and heat-then-dose — since heating and venting land at once and only a dose gives the world fifty seconds. A bed at 20 toward an outside at 8 crosses its floor of 18 in 2 h; foreseeing 6 h, the grower derives an At want and the search, judged at the instant, plans the heater and weighs the vent as no better; toward 21 nothing is foreseen; a forecast turning warm before the crossing warms the bed at the instant and nothing is planned. Three defects found on the way and fixed: a drift's retracted node was trimmed of its type and cancelled nothing in the diff (a pot at 0.12 and 0.100018 at once); a step's own drift never reached its own fork; the imaginarium copied only the graphs holding now, so a forecast for a period the present has not reached was invisible inside a pass |
| 2026-09-12 | `a-predicted-crossing-derives-a-want-met-at-that-instant` | — | — | a predicted crossing derives a want met at that instant (#619): the loner at 0.12 falling at 0.03/day crosses its floor in 16 h; foreseeing a day, the root derives an `orexis:At` want, the pass is clocked from the reading's own instant, rooted at the present drifted to the crossing less the valve's 50 s, and finds the dose in 1 fork, judged one second past the instant (a crossing is the last instant inside an inclusive floor); the keeper places the dose `notBefore` the crossing less 50 s. Two engine facts measured first: no cast turns a duration into a number (only `HOURS`/`MINUTES`/`SECONDS` bind), which is why the pass takes the reading's instant as its clock rather than drifting the reading's age; and a room measured from a fresh clock read made a plan placed exactly at its instant a few milliseconds late — it is measured from the pass clock now |
| 2026-09-12 | `what-is-pursued-is-derived-from-an-always-want` | — | — | what is pursued is derived from an Always want (#618): the planner is untouched and is handed the same shape under the derived want's name, so every world plans exactly as before — hanoi 14 and 50, the courier's corner 71, the greenhouse 128 in both regimes, both plants 2 — and a met root now runs NO pass where it ran a `_begin` and a zero-fork `satisfied` before. The root as LAW was measured and refused: with each root's met-shape added to the never-newly-enter law at violation severity, the loner's dose from dry reads `newly enters a state the society refuses` (2 forks, `not better`), the greenhouse's both regimes 128 → 5 forks and no plan, the loner at 0.42 32 → 2 — because the key (shape, focus, value) names the reading's NODE and a step that replaces a reading mints a new one |
| 2026-09-07 | `the-present-is-identified-among-the-children` | — | — | identification within the want's view (#554, #565's projection): relevance read every variable-predicate retract as writing ANYTHING, which made every want's view the whole world — read now as the construct's own writes, the courier's view is 32 predicates. A present that drifts outside the view resumes; a world that landed in an explored sibling resumes from it, with the plan as good as a fresh one — but not fewer forks: 62 against 50 on hanoi, because worlds under the sibling that the first pass reached cheaper through the winning branch were credited there and go with it |
| 2026-09-06 | `the-cone-outlives-the-pass` | 0.35 s fresh, 0.20 s resumed | — | the cone outlives the pass (#553, closing #487 and #527): measured first, as #527 asked — a fresh pass from the world a surprise leaves costs 355 ms after one hanoi move and 483 ms after two courier steps, so the most a kept cone could save per surprise is under half a second, and it is not built for speed. Built: nodes kept as parent plus two raw lists, graphs dropped when a pass ends and re-made on demand, the present looked up among the kept worlds by its diff, re-rooting by set algebra on absolute worlds, the winner's legality and premises cached on its node. A resumed pass costs 199–203 ms on hanoi against 301–355 fresh, 334–355 ms on the courier against 481–510 fresh; the rest of a resumed pass is signing the invariant half, reading the present's facts and the root's own work. Exact matching, so a plant resumes nothing until #554 |
| 2026-09-06 | `the-frontier-is-scored-by-one-query` | **0.96 s** (was 1.70 s, same run) | — | #552 measured and closed as measured: scoring the frontier (`_met_in` 43 ms, `_estimate_in` 16 ms) is ~6% of a 3-disk solve, so no frontier query was built. What the profile found instead: the construct door asked the store which graphs are the agent's own on EVERY call (~3 ms each, 150 times), and the rule text was fetched per fork by three callers (150 more). Both are remembered per store now, cleared on every write (`Store.remember`, `recorded_graphs` cached like `public_graphs`): store calls 1,365 ms became 263 ms, `apply`'s constructs 343 ms became 22 ms. The plant pass is unchanged at ~310 ms, its cost being the legality selects |
| 2026-09-06 | `a-remembered-plan-is-keyed-by-its-regressed-precondition` | — | — | a remembered plan is keyed by its regressed precondition (#551): the courier's eight-step delivery regresses to 24 facts asked as one select of ~3 kB; `applicable` costs 30–40 ms on a hit (the select plus the first step's menu) and 35–70 ms on a miss, where it asks fact by fact to name the absent one — measured beside a running suite. The measure #551 asked for holds: the same pose with a stray fact beside it adopts the plan with no search where the hash searched again |
| 2026-09-06 | `a-step-carries-its-precondition` | — | — | a step carries its premises (#550): the facts its effect's WHERE and its availability select read, instantiated by the engine as a CONSTRUCT of the WHERE's own patterns, once along the winning path. Parsing the rule text with rdflib was 216 of 276 ms for a two-step plant plan, so the parse is cached per rule text with its tokens kept; filled, a two-step plant plan costs 18–19 ms and a hanoi move 3–4 ms |
| 2026-09-06 | `the-search-judges-by-query` | — | — | a verdict the search reads is a query (#548): the law and the winner's legality compiled to selects (`violation.report_selects`, one per shape) and asked of the imaginarium at the node; on `world/simulation` the legality check 223–287 ms through rudof became 59–65 ms as 75 selects, a whole plant pass 396–454 ms became 192–232 ms, `_begin` 134–164 to 104–167 ms with the border text no longer written; one UNION over all 75 shapes measured 843 ms and was refused; the per-candidate law verdict loses its ~75 ms floor |
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
