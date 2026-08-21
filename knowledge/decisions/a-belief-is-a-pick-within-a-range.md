---
type: Decision
title: A belief is a pick within a range, and an agent may re-pick
description: Beliefs are still authored once at birth, but what genesis wrote is the first pick rather than a bound — the room comes from constraints, and an agent re-picks inside it on evidence about itself.
status: accepted
stage: v1
tags: [beliefs, review, autonomy, constitution, sensing, upkeep]
timestamp: 2026-08-09T00:00:00Z
---

# Context

Two unrelated observations turned out to be the same question.

The first is [issue #45](https://github.com/ShishkinDmitriy/agora/issues/45): a belief base grows
about 4 MB a day per agent while its triple count never moves. It is an LSM tree, every reading
is a DELETE followed by an INSERT, and compaction is size-triggered — so a few hundred triples
never approach any threshold and nothing is ever reclaimed. The remedy is one call. What made it
worth more than a bug fix is *what noticed*: neither number says anything alone. Flat triples are
correct. Rising bytes are alarming only if you already know the triples are flat. The **quotient**
is the signal, and the metrics added in #21 had been computing both halves every minute without
anyone drawing the conclusion.

The second is that `sensing:slowSleepS` is a guess. An author writes "look every ten minutes when
comfortable" before the agent has seen a single reading. Six hours later the agent knows something
the author could not: whether looking that often is telling it anything. Nothing let it act on
that, and the only route to a better number was a human editing a Turtle file.

Both are an agent holding evidence about its own settings with no way to use it.

# Decision — the belief is the pick, the constraints are the bound

The *first* pick answered to nothing when this was written, which is the half it did not cover:
genesis wrote a target and no range bounded it. A plant states the range it needs now, and the
agent's target is a pick inside that — the same shape one level out. See
[the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md).

**A belief is not a constant. It is a point chosen inside a range.** A computer needs one value
to act on, so genesis picks one and the agent lives with it. What genesis wrote is therefore the
*first pick* and nothing more.

This is the correction that shaped everything else. An earlier draft made the authored value a
hard floor — `slowSleepS 600` could relax toward 900 and never go below 600 — which is safe, and
wrong: it **confuses a choice with a constraint**. It also leaves the author's real job unwritten.
If 600 is a bound, nobody ever has to say what the agent's actual limits are; they are an accident
of what number happened to be typed.

So the room comes from constraints, and there are three sources:

| | what it says | where it lives |
|---|---|---|
| **constitution** | what the society allows *any* agent | figures on the capability family, e.g. `sensing:minSleepS` / `sensing:maxSleepS` |
| **hardware** | what the equipment can do | on a device, as an `ssn-system:Frequency` — borrowed from SSN rather than invented, and carried to the agent at genesis. See [a-board-says-what-it-can-honour](a-board-says-what-it-can-honour.md) |
| **mandate** | what **this** agent's world allows it | `review:commits`, in `world.ttl` |

They intersect, and a mandate can only narrow: one looser than the constitution *is* the
constitution.

> **Amended.** The third source was called *self* and lived in the agent's own beliefs, on the
> reasoning that how far an agent will let itself move is its own opinion. That is backwards —
> **an agent constraining itself is not a constraint, it is a choice.** A range is what an agent
> is *allowed*, imposed by whoever ratified its world; the pick inside it is what the agent
> wants, and only that stays private. Range public, value private. Making it public is also what
> made the capability derivable and put the two ends of "a world may not widen the constitution"
> in graphs a single shape can compare. See
> [self-review-is-a-capability](self-review-is-a-capability.md).

The author's job becomes **constraining well rather than guessing well**, and how much autonomy
each agent has stops being implied and becomes a line you can read and diff.

An author who wants a figure fixed writes a mandate with no room in it. **"Leave this alone" is
said by leaving nowhere to go**, not by a flag somewhere that says not to look.

## Which beliefs may move is a fact about the term

One triple, in the `ontology.ttl` of the package that owns the term:

```turtle
sensing:slowSleepS a review:RevisableBelief ; review:revisableToward sensing:minSleepS , sensing:maxSleepS .
```

The reviewer finds it by asking the merged T-Box. Nothing lists it, no Python knows its name, and
which end is which is read from the *values* of the figures a package points at rather than from
the names of the properties pointing at them — so a package names the two limits it already
declares and invents no ordering vocabulary.

This is the property the whole layout exists to have: **adding a capability is adding a
directory.** A capability with an ontology nobody here has read is reviewable on exactly the same
terms as the one shipped with it.

## A rule is SPARQL, not code

`packages/capability/<name>/review.rq`, beside the `rules.ru` that derives the capability itself: one
`SELECT`, rows of `?term ?value` — one row per re-pick, so a package revising two settings ships
one file with a `UNION` rather than two files (sensing does exactly that: the cadence and the
jolt threshold, read off the same evidence window the opposite way round). The rule contains no
number of its own — thresholds come from the constitution, the range comes from the
reviewer, and the evidence is statistics computable without knowing what a property means.

It can read the evidence, the beliefs and the T-Box and do nothing else. A `SELECT` cannot write,
cannot call out, and cannot loop unboundedly — and because **an agent's store already contains
only what it may see**, the sandbox is the isolation design rather than anything added here. That
is [where-the-belief-base-lives](where-the-belief-base-lives.md) paying a dividend it was not
designed for.

Three things a shipped rule cannot know — the agent, its beliefs graph, its evidence graph — are
substituted before it runs. Everything else it discovers.

## Legitimacy is the boot check re-run

After applying, the agent calls `validate_agent` — the identical call `runtime.Agent.__init__`
makes, against the identical shapes — and reverts if it fails.

There is deliberately no second bounds system. A separate "is this revision allowed" checker would
be a copy of the constitution that could fall out of step with it, and the failure would be an
agent legally holding a belief it could not have started with. Reusing the boot check makes that
unrepresentable, and every shape written from now on constrains revisions for free.

A value outside its own range is **refused rather than clamped**: a rule proposing out of range is
wrong about something, and quietly correcting it would hide that.

# A summary is a belief; a reading is a measurement

A rule needs to know whether a probe has been moving, and the store cannot tell it. `sensed_writer`
keeps exactly one observation per subject and property, replaced each reading, because the series
lives in Influx — and that is right.

The answer is not to keep the readings. It is to keep **what they came to**: one summary per
subject and property holding count, extremes, sum and sum-of-squares, from which mean, variance
and spread all follow. Constant size, whatever it summarises.

That line — *a reading is a measurement, a summary is current state* — is exactly the one
[two-store-beliefs](two-store-beliefs.md) already draws between Influx and here, and following it
gives three things at once:

- the triple count **stays flat**, so the guarantee in [agent-metrics](/domain/agent-metrics.md)
  survives and #45's signal is not buried under a growing window;
- the evidence **survives a restart**, so a rebooting agent keeps the grounds for its own
  judgement instead of earning them again — and therefore outlives the code that wrote it, which
  is why boot now checks that the vocabulary still declares what the store holds. Everything
  persisted here is in that scope, not only the beliefs. See
  [a-volume-can-be-older-than-the-vocabulary](a-volume-can-be-older-than-the-vocabulary.md);
- reflection **never waits on the series store**, which attention must never do.

`review:sampleMax` is kept beside the sums although a variance could be derived without it, because
**equality with the minimum is the one thing a variance cannot express**. A variance *approaches*
zero for a nearly-still world and *is* zero only for an instrument that has not moved at all, and
those two cases want opposite responses.

Summaries live in their own graph rather than in `:sensed`. That is what makes the write boundary
checkable: `:sensed` is the measurement record, written by whatever observed and never by a
review, and an invariant nothing can check is a comment.

# The window is the interval between arisings

Not a fixed count. The reviewer closes the accumulating window when it arises, so the evidence is
**everything observed since the last time it looked** — and a short ring of completed windows is
kept behind it, so a rule can tell "steady since I last looked" from "steady for as long as I have
been keeping track", and can see that its own last decision changed nothing.

Every decision — **taken or declined** — records when it is worth revisiting, computed from the
rate readings are actually arriving at: a window's worth of them, and no sooner. Checking earlier
is reading the same evidence twice.

So `review:reviewIntervalS` is a **floor, not a schedule**. It only stops a review planning something
absurdly soon; the decision knows better than the clock does when its own effect could show.

Recording a *decline* is what separates reflection from a twitch. Without it the same question is
re-argued at every arising, and the agent can never reach *"I have declined this eleven times, so
the problem is somewhere else."*

# The stuck sensor, and why steady is not frozen

The obvious rule — *readings are not changing, so look less often* — is wrong in the case that
matters most. A probe reporting exactly 0.412 for six hours is far likelier a stuck ADC than a pot
in perfect equilibrium, and relaxing attention on a broken instrument is precisely backwards: it
is the moment the freshness rule most needs to fire.

So **frozen argues for tightening, alongside moving**; only *steady* — ranging, but by less than
`sensing:steadyFraction` of its own mean — argues for relaxing. Two asymmetries follow:

- **Relaxing needs unanimity; tightening needs one dissenter.** One agent holds one
  `sensing:slowSleepS` covering every sensor it has, so a single moving or frozen instrument pulls the
  whole agent back. The cost of watching a still pot too closely is some battery; the cost of the
  reverse is a dead plant.
- **`sensing:reviewWindow` readings before any conclusion.** Two identical readings are a coincidence,
  and an agent that relaxed on the strength of them would be reasoning from noise.

Both figures are constitutional rather than private. Left to each agent they are the two numbers a
lazy one tunes until it is entitled to stop looking.

# Attention still follows need

`cadence_for` interpolates from `sensing:slowSleepS` toward `sensing:fastSleepS` by urgency, and **only the
comfortable end is revisable**. At urgency 1.0 an agent watches at its fastest whatever a review
concluded. The existing claim — *attention follows need, and need is not sensing's to define* —
stands unamended; what is added is that attention **also** follows whether looking is telling the
agent anything, and the second may only act inside the room the first leaves.

That composition is the whole reason it is safe to let an agent slow itself down.

# Belief-base upkeep is kernel, not a capability

`agora/metrics.py` already argued this: every agent has a belief base whatever else it can do,
capabilities are derived from wiring, and a rule granting a "maintain yourself" capability would
have to fire for everybody — which is the kernel wearing a disguise. Compaction is the same. What
*is* capability-shaped is reviewing something an agent **chose**; keeping your own house is not a
choice.

> **Amended.** Still true, and it acquired teeth: once review became a capability an agent might
> not have, upkeep riding the review timer would have made a mandate-less agent stop compacting
> silently. It runs its own hourly clock now. See
> [self-review-is-a-capability](self-review-is-a-capability.md).

# Consequences

- **"Authored once at birth, never touched by start or stop" still holds**, and is now
  load-bearing differently. Start and stop still never touch beliefs. The agent itself may, while
  running, within its commitment — so a restart no longer returns an agent to the sovereign's
  opinion, and `genesis.birth` refusing to overwrite is what preserves that.
- **An agent's behaviour is no longer fully reproducible from its files**, and that is the price.
  What replaces it is the revisions graph: every decision records the term, the values either
  side, the evidence in words, the time, and when to look again. An agent that cannot say why it
  changed its mind — or why it did not — has not reviewed anything.
- **Every world's files grew a mandate.** That is the cost of moving the author's job from
  picking to constraining, and it is the readable half of the change. It went into the beliefs
  files first and belongs in `world.ttl` — what an agent is *allowed* is a governance fact, not
  an opinion it holds about itself.
- **Derived numbers are rounded on the way into the store.** A Python float divided to full
  precision produces nineteen-digit decimals, which the store accepts and returns and then fails
  to compare — and a SPARQL `BIND` whose expression raises leaves its variable *unbound while
  keeping the row*. A rule then silently produces a solution binding nothing rather than an error,
  which is the most expensive shape a bug can take. `store.decimal` exists for that reason.

# Seams left open

- **No device states a sensor constraint.** The third source of room is declared and intersected
  and nothing uses it. It is real the moment a board says what interval it can honour.
- **Only instrument settings are reviewable** — `sensing:slowSleepS` and, since the jolt threshold
  became a pick, `sensing:alarmDeltaFraction`. Instruments only, deliberately. An agent revising what
  it *wants* — a target, a band, a price — is a much larger claim than one revising how often it
  looks: it could satisfy itself by wanting less, which is the failure the band exists to make
  visible. In BDI terms this is just another desire and could be specified properly; it has not
  been.
- **Rules are shipped, never derived.** A capability with no `review.rq` is not reviewed, so the
  T-Box discovery is currently more general than anything using it. The intended next step is an
  LLM that proposes a *rule* rather than a value — the society then accumulates auditable decision
  procedures instead of decisions — and how such a rule would be ratified is undecided.
- **Evidence is not scoped by sense mode.** A moving thermometer would tighten the cadence of a
  moisture probe on the same agent. No ratified world has that shape yet; see
  [#51](https://github.com/ShishkinDmitriy/agora/issues/51).
- **The reviewer arises on a clock, not on surprise.** A decision's due-date paces it, but nothing
  wakes an agent because something contradicted what it believed.
