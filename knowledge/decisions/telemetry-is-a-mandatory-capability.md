---
type: Decision
title: Telemetry is a mandatory capability, because mandatory and uniform are different questions
description: >-
  ag:SelfReporting claimed to be a capability directly above a comment saying it is granted to
  nobody, and it sat in the kernel because grant-universality and implementation-uniformity
  were being treated as one question. They are not — rule 2 asks whether the HOW could differ,
  not whether every agent has it. Reporting becomes a package granted to every agent by a rule
  and insisted on by a shape; counting stays in the kernel, because counting is the part that
  could not differ. What latitude grants is publishing which value an agent settled on, and
  that is #61.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

[every-term-in-its-own-house](every-term-in-its-own-house.md) moved 102 terms into their packages
and left eleven in the kernel that are not true of every agent. `ag:SelfReporting` was one, and it
was a different kind of wrong from the rest: not misplaced, but **self-contradictory**.

```turtle
ag:SelfReporting a owl:Class ; rdfs:subClassOf ag:Capability ;
    rdfs:comment "… NOT derived and NOT composed onto anyone: every agent reports …"
```

The axiom says capability; the prose on the next line says it is granted to nobody and held by
everybody. It appeared in no world, no `rules.ru` granted it, and nothing enumerates subclasses of
`ag:Capability` — so it leaked into no behaviour. A capability that nothing grants and nothing
requires is a convention, not a fact.

# The question that was being asked wrong

It looked like a choice between *capability* and *kernel function*, and both answers had evidence
behind them, which is the tell that the question was malformed.

**Two questions were collapsed into one:**

| | |
|---|---|
| **grant universality** | does *every* agent have it? |
| **implementation uniformity** | could the *how* differ? |

[AGENTS.md](../../AGENTS.md) rule 2 asks only the second — *a capability is a named ability with
interchangeable implementations* — and says nothing about who holds it. So **a capability every
agent holds is still a capability**, provided its members are genuinely interchangeable. What it
is not is *optional*.

That dissolves the conflict instead of picking a side, and both halves of the evidence survive
intact.

# Decision — a package, granted unconditionally, insisted on by a shape

`packages/capability/reporting/`, with its own namespace, ontology, shapes, rule, beliefs and
module. `reporting:Storing` is implemented; `reporting:Announcing` is declared with nothing behind
it, exactly as `review:Consulting` and `sensing:Polling` are.

**Granted by a rule whose premise is being an agent:**

```sparql
INSERT { GRAPH $derived { ?agent ag:hasCapability reporting:Storing } }
WHERE  { ?agent a ag:Agent }
```

Derived, never declared — `world.ttl` still contains no `ag:hasCapability` and the prohibition is
untouched.

**And insisted upon.** `reporting:EveryAgentReportsShape` refuses an `ag:Agent` holding no member
of the family. That is what makes *mandatory* a fact the world is held to rather than a convention
nobody checks, and it is the difference from the state this record replaces. Verified by disabling
the grant: three worlds go from `Conforms: True` to `Conforms: False`, with *"every agent must
report on itself — no agent may be silent by construction, or a quiet one cannot be told from a
dead one."*

## Why it must not be conditional

This is the half that does not change, and it is worth stating because a later reader will be
tempted by the symmetry with `review:Reckoning`.

- **A silent agent and a dead one must stay distinguishable.** Health telemetry is the only thing
  that can tell them apart. An agent that could lose the ability to say it is unwell is precisely
  the one you most need to hear from.
- **[#53](https://github.com/ShishkinDmitriy/orexis/issues/53)** — *an agent can lose its broker
  session for days and nothing says so* — would become permanently unfixable for exactly the
  agents that cannot speak for themselves.
- **A merged record already depends on it.**
  [self-review-is-a-capability](self-review-is-a-capability.md) reads absence as a signal:

  > `belief_compactions` comes off the kernel and **every agent reports it**; the revision counts
  > come off a module an agent may not have … so the **absence** of those lines in the series is
  > itself the reading: this agent was never granted any latitude.

  That only works if the agent is still reporting. Granting reporting by latitude would destroy
  the signal *silently* — the series would look identical to an agent that had simply gone quiet.

`succulent` is the worked example, and the test now says so in one line: its cadence is pinned, so
it holds no `review:Reckoning` and does hold `reporting:Storing`. Mandatory and granted, in one
agent, visible in one assertion.

# Counting stayed in the kernel, and that is where the family gets its members

The split is the same test applied twice. **Counting could not be done differently**: every agent
counts the same figures, and `Observations` counts into them before any module exists. So
`agent/metrics.py` keeps the mind's own account — `uptime_s`, `belief_triples` — and every package its own, merged by reporting ([metrics-are-an-aspect](/decisions/metrics-are-an-aspect.md)); this said `mqtt_connected`,
`mqtt_reconnects`, the write failures, `world_version`, reading-age per sensor.

**Where the account goes could differ**, and that is the module: a credential, a writer, a clock,
one write per tick. `reporting:Announcing` would take the same `agent_fields()` and publish it on
the bus.

Those two fail **independently**, which is the reason that member is worth naming rather than
imagined. An agent whose series credential is wrong or whose bucket is gone can still announce;
the converse holds too. It also has a limit worth saying out loud: a member reporting over the bus
cannot report having lost the bus, which is exactly the fault #53 is about. Redundancy here is a
second path, not a complete one.

## The trap in the sink argument

An earlier pass concluded this was a function on the ground that a sink is a service URL, and
AGENTS.md puts those in **environment**, *"because they are not beliefs anyone holds"*.

That argument is about **where a sink's address lives**, and it is correct about that. It says
nothing about whether the *manner* of reporting is pluggable. A member is a way of reporting; its
endpoint is still `INFLUX_URL`'s neighbour. Conflating the two is what made a family look like a
function, and it is the same shape of error as collapsing mandatory into uniform.

# The interval stops being optional

Its absence used to mean an agent reporting nothing — a decision stated by omission, in the idiom
of a beliefs file with no bidding block. It is now an ordinary required parameter of the
capability, exactly as `review:reviewIntervalS` became.

**No world ever exercised the branch.** All nine agents across all three worlds state an interval,
so the thing that made this look like a choice was made by nobody. That is *"a side channel
dressed as a decision by omission"* — `self-review-is-a-capability`'s phrase for the identical
pattern, refused for the identical reason.

And the branch was incoherent on its own terms: an agent permitted to report nothing produces
silence that carries no information, which is the one thing telemetry exists to prevent. The old
argument was that refusing to boot over instrumentation is disproportionate, and it assumed
telemetry is a nicety. It is the thing that tells you the rest is working. A missing series
*credential* was already fatal in `observation.py`; the interval is now merely consistent with it.

A missing credential is still not fatal, and the distinction is deliberate: an operator can fix an
environment variable without re-ratifying a world, so that stays a loud warning while a missing
belief refuses.

# What latitude grants, and it is not this

The instinct that sent this back for a second look was right about something real. There **is** a
latitude-shaped capability here; it is not health telemetry.

An agent with no room to move has settings that are exactly what genesis wrote — readable from
`world.ttl` and its beliefs file by anyone holding the files. An agent with `review:commits`
latitude has **re-picked** something, and that value exists nowhere but inside it. Publishing
*which value it settled on* is therefore meaningless without a settled value, invisible from
outside, and granted by exactly the premise `review:Reckoning` is granted by.

That is [#61](https://github.com/ShishkinDmitriy/orexis/issues/61) — *nothing outside an agent can
see which value it settled on*. *(Closed since, and the split above is exactly how: the
`picked_<package>_<term>` fields are contributed by the REVIEW module through `reports()` — the
latitude-granted module, so the fields exist on exactly the agents whose values could be
elsewhere than authored — and they ride the mandatory reporting sink into the agent's own
bucket, where the operator's read token sees them and a rival's cannot. A taken or refused
revision is also a marker over the series, through the same event channel the intention story
rides; declines stay a count, being the routine outcome of most arisings.)*

| | what it reports | granted by |
|---|---|---|
| health telemetry | how the agent *is* — uptime, connection, disk, freshness | nobody: every agent, always |
| settled values | what the agent *decided* — the point it re-picked inside its range | latitude, like `review:Reckoning` |

Both are "an agent reporting on itself", which is why one name covered them and why the question
kept coming back. They are not the same fact, and only the second could ever be absent.

# Consequences

- **`agent/ontology.py`'s claim gets closer to true.** Its docstring listed eleven kernel terms
  that are not universal; ten now, and this one left by becoming a package rather than by
  ceasing to claim something.
- **Every agent runs one more module.** `reporting` appears in every module set, which two
  runtime tests now assert.
- **An agent with no interval refuses at boot** rather than coming up silent.
- **#61 has its premise written down** before anyone builds it, which is most of why settling this
  was worth more than deleting the term.

# Seams left open

- **Nothing selects between members.** With one implemented the rule names `reporting:Storing`
  directly, the same way review's names `review:Reckoning`. What would choose once
  `reporting:Announcing` exists is undecided — and unlike sensing, no hardware fact forces the
  answer.
- **`Block.capability` is a misnomer for one of its uses no longer**, which is a small gain: the
  block now names a real capability like every other.
- **A member reporting over the bus cannot report losing the bus.** Worth knowing before building
  the one this record recommends.
- **Nothing checks that a declared capability is granted by something.** This one was found by a
  sweep that happened to read every term. A test could ask it of every `rdfs:subClassOf
  ag:Capability`, and none does.
