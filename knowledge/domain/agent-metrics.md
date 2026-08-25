---
type: Domain Concept
title: What an agent says about itself
term: http://example.org/orexis/reporting#ReportingCapability
description: The figures an agent is uniquely placed to report — belief base size, reading freshness, and the write failures that were previously only logged. Counting is the kernel's because it could not be done differently; where the account GOES is a mandatory capability, granted to every agent and insisted on by a shape. The interval is required, because an agent permitted to be silent cannot be told from a dead one.
---

# What it is

Every agent reports on itself on a slow clock, into its own series bucket. Not on the world, not
on its plant — on **itself**: how big its belief base has become, how long since a sensor last
delivered, how many writes it lost, how long it has been up.

```bash
# in that agent's beliefs, and nowhere else
ag:fern_agent reporting:metricsIntervalS 60 .
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
| `belief_triples`, `belief_bytes` | **expected to be flat.** `sensed_writer` deletes before it inserts, and a summary is running totals rather than samples, so an agent holds a fixed number of nodes however long it runs — set by its wiring, not by its uptime. A rising line means something started appending, and that is the failure this number exists to catch. `belief_bytes` used to rise regardless, because RocksDB grows on disk while the triple count does not move; it is now a sawtooth, because their **quotient** triggers a compaction. See [a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md). |
| `belief_compactions` | how often the agent reclaimed its own write amplification. This is why the `belief_bytes` line now has teeth: the pair of numbers that revealed the problem is the pair that fixes it. |
| `belief_revisions`, `belief_reviews_declined` | settings the agent re-picked, and times it looked and concluded no. Both matter: a conscience that reported only its changes would look identical whether it was thinking hard and declining, or not arising at all. A rising `belief_revisions` means this agent is no longer running exactly what its author wrote — and its revisions graph can say why, in words. |
| `belief_revisions_refused` | proposals the shapes rejected. **Flat at zero is the assurance**: it says every rule is proposing only what the constitution already allows. A rising line is a bug in a rule, not a misbehaving agent. |
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

# Counting is the kernel's; reporting is a capability

The two halves answer different questions, and treating them as one kept the whole of this in the
kernel for longer than it belonged there.

**Counting could not be done differently.** Every agent counts the same figures, and
`Observations` counts into them before any module exists — so the account itself is the kernel's,
on the same argument that put [observation](/decisions/capability-packages.md) there.

**Where the account goes could differ**, so that is `packages/capability/reporting/`: a credential, a
writer, a clock and one write per tick. `reporting:Storing` puts it in this agent's own series
bucket; `reporting:Announcing` — declared, unimplemented — would put it on the bus, and the two
fail independently, which for telemetry is the point rather than a nicety.

**Mandatory is not the same as uniform.** Every agent is granted this by a rule whose premise is
being an agent, and a shape refuses an agent without it. [AGENTS.md](../../AGENTS.md) rule 2 asks
whether the *how* could differ, not whether everyone has it — so a capability everybody holds is
still a capability, and what it is not is optional. See
[telemetry-is-a-mandatory-capability](/decisions/telemetry-is-a-mandatory-capability.md).

This page used to argue it the other way round — *"not derivable from wiring, and capabilities are
derived from wiring"* — which reached the right conclusion by a reason that has since been
superseded twice: [self-review-is-a-capability](/decisions/self-review-is-a-capability.md) grants
one by latitude, and [the wire's record](/decisions/the-wire-is-ours-and-it-has-two-levels.md)
grants others by what a device speaks.

# The interval is a belief, and it is required

A rate belongs in beliefs for the same reason the sensing cadence does: a test world may want it
faster than a deployed one, and that is the agent's own parameter rather than the world's
topology.

It used to be optional, and an agent that stated **no** interval reported nothing. That is gone,
for two reasons that only look like one:

- **No world ever used it.** All nine agents across all three worlds state an interval, so the
  branch that made this look like a choice was exercised by nobody — *"a side channel dressed as
  a decision by omission"*, which is
  [self-review-is-a-capability](/decisions/self-review-is-a-capability.md)'s phrase for the same
  pattern, refused there for `review:reviewIntervalS`.
- **An agent reporting nothing produces silence that says nothing.** The value of health telemetry
  is that quiet means something; an agent permitted to be silent is indistinguishable from a dead
  one, and that is the case you most need to tell apart.

So a missing interval refuses at boot like any other missing belief. A missing series *credential*
still does not, and the difference is deliberate: an operator can fix an environment variable
without re-ratifying a world, so that stays a loud warning.

# The dashboard

`orexis-dashboards <world>` generates a second dashboard per world, `health.json`, derived from
the **roster** rather than the wiring — every agent, not only the ones that observe, because a
market host owns a belief base and can go quiet exactly as loudly as a sensing agent can.

One panel carries one target per agent, because each agent owns its own bucket and there is no
union to be had: an agent's token opens only its own, and the only client that can see all of
them at once is Grafana, holding the read-only token minted for exactly that. See
[series-and-bus-isolation](/decisions/series-and-bus-isolation.md).

# The picks beside the counts

`belief_revisions` says *that* an agent changed its mind; since #61 the review module also
contributes `picked_<package>_<term>` — the current value of every revisable term the agent
holds. Contributed by the latitude-granted module, not by reporting itself, so the fields exist
on exactly the agents whose values could be elsewhere than authored; an agent with no mandate
is silent on them, and that silence is the reading. The governance surface this opens: a whole
society relaxing the same figure to its ceiling is the strongest evidence a range was
mis-authored that this design can produce, and an author who cannot see how latitude is used
grants narrow ranges — which is the same as granting none.

# The story beside the figures

The counters say *that* something happened; since #125 the kernel also buffers **events** —
point-in-time transitions with their prose. The [intention](/domain/intention.md) ledger tells
`Metrics.event()` at every adoption, resolution and end-verdict, carrying the `becauseOf` text;
the reporting capability drains the buffer on its ordinary tick, through the same writer, token
and bucket, into a third measurement (`agent_events`, each point stamped with the transition's
own instant); and the health dashboard draws each agent's stream as **annotations** over every
panel — `worst_gap` climbing with an `adopted Acquire: "bid 0.4L …"` marker at the knee is the
view the ledger was built to make possible.

Three properties keep it honest: the buffer is **bounded** (the graph is the record, this is a
projection for eyes, so under a long outage the oldest markers are the right casualty); a
failed write hands the drained events **back** (a figure missed is superseded by the next
tick's, a transition missed is gone); and the text is **prose that must never be parsed** — the
same contract as `ag:becauseOf`, whose projection it is. An agent without the intention
capability tells no events and writes none; nothing new is granted anywhere.

# Seams left open

- **Counters reset on restart.** `readings_total` and the failure counts are since boot, so a
  crash loop looks like a series of small numbers rather than one large one. `uptime_s` is what
  disambiguates it, and nothing joins them for you.
- **Nothing alerts.** These are series on a dashboard; a write failure climbing at 3am is visible
  and unannounced. One figure now *acts* instead of waiting to be read: the disconnection clock,
  which the transport's watchdog turns into a resignation past `ag:resignAfterS` — see
  [a-dead-session-is-resigned-not-endured](/decisions/a-dead-session-is-resigned-not-endured.md).
  Everything else still only shows.
- **A report that fails is not counted.** The gap in the series says it, and a counter of
  failures-to-report-failures earns less than it costs.
- **The sensor set is the union of wired and delivered**, which is right but means a sensor
  removed from a world keeps reporting until the agent restarts.
