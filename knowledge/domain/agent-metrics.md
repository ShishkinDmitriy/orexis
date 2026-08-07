---
type: Domain Concept
title: What an agent says about itself
description: The figures an agent is uniquely placed to report — belief base size, reading freshness, and the write failures that were previously only logged — why they live in the kernel rather than a capability, and why the interval's absence is a decision rather than a default.
tags: [metrics, observability, kernel, beliefs, dashboards]
timestamp: 2026-08-06T00:00:00Z
---

# What it is

Every agent reports on itself on a slow clock, into its own series bucket. Not on the world, not
on its plant — on **itself**: how big its belief base has become, how long since a sensor last
delivered, how many writes it lost, how long it has been up.

```bash
# in that agent's beliefs, and nowhere else
ag:fern_agent ag:metricsIntervalS 60 .
```

# Why the agent and not something watching it

Each figure here is one only the agent can state.

Nothing else can count the triples in its belief base, because
[nothing else can reach it](/decisions/where-the-belief-base-lives.md) — that is the whole
isolation design. Nothing else knows how long it has been since a reading arrived, because a gap
is only visible from the end that was waiting; a monitor watching the store sees an absence of
rows and cannot tell a quiet board from a dead agent from an empty bucket.

Both of those were computed by hand during bring-up. The freshness one was worked out by pulling
every stored reading and differencing timestamps, which produced a real answer — a median gap of
19s against a 10s cadence, a worst gap of 44.9 minutes, and 88% of the window spent in dropout —
and took a bespoke script to get. An agent knows all of it directly and was not being asked.

# What it reports

| | |
|---|---|
| `belief_triples`, `belief_bytes` | **expected to be flat.** `sensed_writer` deletes before it inserts, so an agent holds one current observation per subject *and property* however long it runs — a fixed number, set by its wiring. A rising line means something started appending, and that is the failure this number exists to catch. (`belief_bytes` is flat only in principle; see [#45](https://github.com/ShishkinDmitriy/agora/issues/45) — RocksDB grows on disk while the triple count does not move.) |
| `reading_age_s` | per sensor, seconds since it last delivered. Absent until it has delivered once. |
| `readings_total` | per sensor, since boot. Zero is the "this board has never once been heard from" signal, which is a different fault from a board that went quiet. |
| `influx_write_failures`, `sensed_write_failures` | since boot. |
| `mqtt_connected`, `mqtt_reconnects` | a marginal link shows here before anywhere else. |
| `uptime_s` | resets on restart, which is how a crash-looping agent announces itself. |
| `world_version` | which world it is **running**, not which is on disk. A world can be re-ratified while agents keep running what they booted with. |

**The two failure counters are the highest-value entries.** `observation.py` caught both
exceptions and logged them, which made lost data invisible: nothing reads a container's log until
something is already known to be wrong, so a store that had quietly stopped accepting writes
looked exactly like one that was working. They are still caught — a reading must not be dropped
because the history could not be kept — but they are now counted, and a dashboard flat at zero is
the evidence that nothing is going missing.

# Kernel, not a capability

Every agent has a belief base, a connection and an uptime, whatever it composed, and the value is
in *all* of them reporting rather than whichever opted in. The same argument that put
[observation](/decisions/capability-packages.md) in the kernel: a thing every agent does is not
one capability's business.

It is also not derivable from wiring, and **capabilities are derived from wiring** — so making
this one would have required inventing a rule that fires for everybody, which is the kernel
wearing a disguise.

# The interval is a belief, and its absence is a decision

A rate belongs in beliefs for the same reason the sensing cadence does: a test world may want it
faster than a deployed one, and that is the agent's own parameter rather than the world's
topology.

An agent that states **no** interval reports nothing. That is not a silent default — it is a
decision stated by omission, in the same idiom as a beliefs file with no bidding block saying
this agent holds no stake. It is read with `read_optional`, which returns nothing for a wholly
absent block and still refuses for a *partially* present one, because half an answer is an
authoring slip rather than a choice.

Refusing to boot over instrumentation would be disproportionate. An agent that cannot report is
still an agent; one that cannot record is not — which is why a missing series credential is fatal
in `observation.py` and merely loud here.

# The dashboard

`agora-dashboards <world>` generates a second dashboard per world, `health.json`, derived from
the **roster** rather than the wiring — every agent, not only the ones that observe, because a
market host owns a belief base and can go quiet exactly as loudly as a sensing agent can.

One panel carries one target per agent, because each agent owns its own bucket and there is no
union to be had: an agent's token opens only its own, and the only client that can see all of
them at once is Grafana, holding the read-only token minted for exactly that. See
[series-and-bus-isolation](/decisions/series-and-bus-isolation.md).

# Seams left open

- **Counters reset on restart.** `readings_total` and the failure counts are since boot, so a
  crash loop looks like a series of small numbers rather than one large one. `uptime_s` is what
  disambiguates it, and nothing joins them for you.
- **Nothing alerts.** These are series on a dashboard; a write failure climbing at 3am is visible
  and unannounced.
- **A report that fails is not counted.** The gap in the series says it, and a counter of
  failures-to-report-failures earns less than it costs.
- **The sensor set is the union of wired and delivered**, which is right but means a sensor
  removed from a world keeps reporting until the agent restarts.
