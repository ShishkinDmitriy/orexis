---
type: Runbook
title: Measure a pass
description: >-
  How to time a whole agent's pass on a shipped world - the greenhouse's grower booted, readings
  delivered, one pass run - held to what the pass did and timed by the agent's own events, the
  runtime's laps and the Planner's; how to record a row in the pass ledger; and what the first
  figures say. The search's own bench is measure-the-search; this is the agent around it.
---

# Why a second bench

[measure-the-search](/runbooks/measure-the-search.md) times the Planner on a problem that is all
search: no sensing, no revision, no executor. What a deployed agent pays per reading is the whole
pass — the bytes sensed into an observation, its sides concluded, the prediction rewritten, the
derivation, the search, the plan published and adopted, the executor's walk — and until this bench
that figure lived in a comment (`tools/run-world-end-to-end.sh` said "about 0.4 s"), with no commit
and no machine beside it. A number without those is an impression. This bench makes it a ledger row.

# How to measure

```bash
pytest world/greenhouse/tests/test_bench.py -s -n0                 # print the figures
pytest world/greenhouse/tests/test_bench.py -s -n0 --bench-record  # and append them to the ledger
```

`world/greenhouse/tests/test_bench.py` boots the grower from `world/greenhouse` as
`world/greenhouse/tests/test_greenhouse.py` does — a fake broker, a clock that ticks per read —
delivers the readings and runs `Runtime.run(passes=1, poll_s=0)` once, five times from a fresh
boot, and reports the median with each lap's median beside it. Four cases, each asserted on what
the pass DID and never on what it cost:

| case | readings | what the pass must do |
|---|---|---|
| `cold_dry_bed` | 12 degrees, 0.2 | two wants in two scopes, the pump's and the heater's commands |
| `comfortable_bed` | 21 degrees, 0.45 | nothing — the price of a quiet pass |
| `framed_cold_dry_bed` | the cold dry bed and a cold frame beside it at 5 degrees | three scopes, the heat lamp's command with the other two |
| `dose_and_heating_answered` | the cold dry bed dosed, then 21 and 0.45 eleven minutes on | both intentions `done`, nothing new sent — the warm pass of a running agent |

The frame is `world/greenhouse/tests/conftest.py`'s `framed_greenhouse`, the copy
`world/greenhouse/tests/test_scaling.py` holds the soil's search flat under. The ledger's rows before
2026-10-10 name the third case `lit_cold_dry_bed`, a light on the bed and a lamp raising it, which
the heating could fill until it came to speak the air's state (#944); the two are not one series.

**The clocks are the agent's own.** Nothing here times a second way: the bench connects to the
runtime's `passed` and the Planner's `planned` exactly as the metrics part does, so what it reads
is what a monitored agent reports — `Passed.duration_s` for the pass, `drain_s`, `plan_s` and
`execute_s` for the runtime's parts, and `Planned`'s `ground_s`, `weigh_s`, `derive_s`,
`search_s` and `publish_s` for the Planner's. A bench with a clock of its own would drift from
the dashboards, and the day the two disagreed nobody would know which to believe.

# How to read a row

- **drain** is the jobs queued before the timers run: the readings sensed, each observation
  revised and its sides concluded, the prediction rewritten, and the walk a revision of the
  present queues. In the warm case it is where the intentions end, which is why it is the
  largest lap there.
- **plan** is the planning package's job, and it is MORE than the Planner's five laps: the
  difference is adoption and what it sets off — each plan published is adopted by the executor
  inside the Planner's own signal, the committed step is written, revised and predicted over —
  and `_keep`'s reads. On the cold dry bed the five laps sum to 115 of plan's 187 ms.
- **ground** is `prepare_ground` and `lay_ground` per scope, which is why it is the lap that
  grows with a scope added: one scope more and ground trebled where the search merely doubled.
- **execute** is the walk the pass asks for after planning, the heads due looked at.

**A lap is from the last mark.** The runtime's `drain` read twelve microseconds on the first run of
this bench, while two readings were being sensed; the executor's walk, queued by a revision and run
among the drain's jobs, marked `execute` there and took sensing's time with it. The hand-timed
drain was 52 ms, and so it reads now that only the walk a pass asks for marks the lap
(`agent/execution/create.py`). A column that says nought while work is plainly being done is the
first thing to doubt in a new row.

**The machine drifts, here too.** Two serial runs of the same tree minutes apart gave the cold dry
bed 343 and 254 ms. A/B is alternated within one session or it is not a measurement, as the search
runbook says.

# The ledger

**The ledger is `world/greenhouse/tests/bench/results.tsv`**, one row per case per recorded run:
the date, the commit (`-dirty` where the tree had uncommitted changes), the machine, the case, the
runs, the median and minimum milliseconds of the pass, every lap's median in milliseconds, the
belief base in quads, the wants searched and the commands sent. It is appended, never rewritten, and
it refuses to be written under xdist. Its columns are not the search ledger's — a pass is laps
where a search is statements — so it is a ledger of its own.

The first rows, 2026-10-04, the development container, at `0bce1144-dirty` — the tree that became
the commit adding this bench — medians of five:

| case | pass | drain | plan | execute | ground | search | quads | wants | commands |
|---|---|---|---|---|---|---|---|---|---|
| `cold_dry_bed` | 254 ms | 58 | 187 | 9 | 56 | 40 | 1397 | 2 | 2 |
| `comfortable_bed` | 96 ms | 51 | 45 | 0 | 10 | 22 | 1299 | 0 | 0 |
| `lit_cold_dry_bed` | 524 ms | 94 | 403 | 17 | 173 | 77 | 1562 | 3 | 3 |
| `dose_and_heating_answered` | 220 ms | 126 | 85 | 0 | 26 | 27 | 1369 | 0 | 0 |

What they say. A quiet pass is about a tenth of a second here, half of it sensing two readings and
half the Planner finding nothing to do; the cold dry bed is two and a half times that, and the
difference is almost all `plan`. The third scope doubles the pass, and most of that is ground, 56
to 173 ms, since `prepare_ground` copies the beliefs once per scope; that fixed price per scope
is the one [a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md)
weighed against the worlds a split saves. The warm pass answering both steps spends more in the
drain than the cold one did, because the intentions end there. None of these is the 0.4 s the
end-to-end script quotes for the Pi; that figure is the Pi's, and the next rows from the bench Pi
will say by how much.
