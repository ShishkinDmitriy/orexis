---
type: Runbook
title: Reflect
description: >-
  How to ask one agent's series what a season says - orexis-explain over its history and metrics
  buckets with the admin-side token, or over the points a run's sinks recorded, never its beliefs -
  what each of the five fixed questions reads and names, what the world's documents are read for,
  and the first figures from the greenhouse played in-process. The measurement the issue asks for,
  the containers at pace 600 for a real hour, is still to be run.
---

# What this is

[reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md)
decides that reflection reads an agent's [series](/domain/kernel/series.md) and never its beliefs,
answers a fixed set of questions first, and offers the sovereign a proposal in the world's own words.
`orexis-explain` is the first tool: the model-less half, a report that answers the fixed set. It is
the model's tool before it is the person's — a model asked to reflect would read this report, not the
buckets — and nothing here wires one. It asks the season and never the present: what an agent wants
and does now is its account
([an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md)).

# Against a live store

```bash
orexis-explain greenhouse grower               # everything the two buckets hold
orexis-explain greenhouse grower --since 30d   # a Flux duration back from now, or an RFC 3339 instant
```

It reads `greenhouse-grower`, the history, and `greenhouse-grower-metrics`, the metrics, in the store
`infra/installation.ttl` says serves each purpose, with the admin token `orexis-influx` reads from
`infra/secrets/` — which is why the command lives in `onboarding/` beside the grants and outside the
agent image, as `onboarding/influx.py` does ([onboarding](/domain/onboarding/onboarding.md)). A
world that is not `onboarding:monitored` writes no metrics, and the report says so: four of the five
questions then have nothing to read, and the fifth answers from the history alone.

The world's documents are read for two things the series cannot say, and nothing else: which desires
the agent holds — a desire never read unmet leaves no trace on the series, so the agent is booted from
its documents in memory, as `reading.lasts` boots one, and asked — and which sensors read a fraction of
one, a `unit:UNITLESS` on the sensor or on the range its host states for the property, so that "past
1.0" is asked of a probe and never of a thermometer. No volume is opened.

# Over a run's points

The questions run over rows, and the rows are the points a `Sink` was handed: `report(world, agent,
history, metrics, stated)` in `onboarding/explain.py` takes two lists of them and a `Stated` of the
desires and the fractions, and `points_of` pivots a store's rows — one per field — back into the same
points, so the two paths meet at one shape. A test installs a sink that keeps the points and runs the
report afterwards, as `world/greenhouse/tests/test_explain.py` does with the greenhouse played by its
simulator, a metrics window a pass long (`metrics.configure(interval_s=0)`) and no InfluxDB in the room:

```bash
pytest world/greenhouse/tests/test_explain.py -n0 -s                        # a simulated day, the figures printed
OREXIS_EXPLAIN_HOURS=120 pytest world/greenhouse/tests/test_explain.py -n0 -s -k season   # five days
```

# What each question reads

| section | reads | names |
|---|---|---|
| wants nothing reached | `unreachable` by `desire`: passes, windows, span | an action the world lacks, or a scope that cannot reach the want |
| landings | `landing` by `action`: verdicts, landed, timed out, `late_s` mean and max; the history's `Step` points taken and landed | a landing band declared wrong, or an instrument past its calibration; a line that timed out or did not land says STOOD OUT |
| desires never unmet | the desires held, less those any `search` is tagged with | dead weight, a desire to retire |
| searches exhausted | `search` by `desire` where every `outcome` is `Exhausted`: searches, `budget`, `weighed` | a budget too small or an estimate too weak |
| probes | per `sensor` and measurement: stretches past 1.0 or below 0.0 where the reading is a fraction; the longest run of an unchanged `raw`; the windows `doubted` said it `silent` or `stuck` | a recalibration to schedule |

`late_s` is the executor's: the instant a verdict was reached less the `landsAt` the plan placed, in
the agent's seconds, so a dose answered by the next reading reads a cadence late by construction; the
distribution is for reading against the action's declared band, not against nought. The fifth reads
the two fields #894 put on the series for it — `raw` beside `value` on every observation point, and
`doubted` per sensor — so a point written before #894 answers the stretches and not the runs.

# Figures

The greenhouse played by its simulator in-process on the development container, 2026-10-04, at the
tree that became the commit landing this: a reading every ten minutes from the thermometer and the
probe, the bed drying by the world's `climate:driesPerDay`, the grower dosing it when it reads below
its floor, both sinks recording, a window a pass long.

| season | passes | run | history points | metrics points | report | what it said |
|---|---|---|---|---|---|---|
| 24 h | 144 | 30.9 s | 290 | 1,736 | 1.4 ms | one `Dosing` verdict, landed, `late_s` 600 s — the next reading; nothing else stood out |
| 120 h | 720 | 221.6 s | 1,444 | 8,656 | 7.7 ms | two `Dosing` verdicts, both landed, `late_s` 600 s; nothing else stood out |

What the two seasons say. Four sections answer *nothing stood out*, and that is the correct answer for a
world that works: no want unreachable, the one desire searched every pass, no search exhausted, no
reading past a calibration point, no raw count repeated — the simulated instrument jitters (#879), so
the longest run is one reading — and no sensor doubted. The landing's 600 s is the greenhouse's
cadence: a dose is seen to have landed when the next reading arrives, and the bed, dosed to 0.45 and
drying by 0.04 a day, crosses its floor again under four days later, which is the second dose. The
report itself is milliseconds — 1.4 over two thousand points, 7.7 over ten thousand, linear in the
rows — where a season of a real agent at a ten-minute cadence is some fifty thousand history points a
year and a metrics point per measurement and tag set per window, so the read from the store will be
the cost, not the answer.

**Still to measure, the issue's own figure:** `world/greenhouse` under the containers at
`OREXIS_TIME_PACE=600` for one real hour — twenty-five agent-days — monitored, then
`orexis-explain greenhouse grower` against the live store, with the points read, the read's time and
what each question answered recorded here. It needs the broker and the store up and a world brought
up, which is the dispatching session's to do; the in-process figures above are the stand-in.
