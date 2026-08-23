---
type: Decision
title: Freshness follows the cadence, except where the agent does not set it
description: A subscribing agent chose how long to wait between readings, so an absolute staleness limit contradicts its own instruction. Why the rule is relative for sensing:Subscribing and absolute for sensing:Listening, and why "I do not know" is not the same answer as "I am fine".
status: accepted
timestamp: 2026-08-07T00:00:00Z
---

# The contradiction

Every agent held both of these:

```turtle
sensing:slowSleepS 600       # comfortable: let the board sleep, save energy
sensing:maxReadingAgeS 120   # older than this and it will not bid on the number
```

The first says six hundred seconds of not looking is acceptable. The second says anything over a
hundred and twenty seconds old cannot be relied on. They are both the agent's own beliefs and they
disagree, so whenever the plant was comfortable the agent guaranteed its own readings went stale —
and then reported it as `my sensor did not answer in time`, which was false. The sensor had
answered exactly as instructed.

# Three states, one signal

The deeper fault is that the agent had one way to say three different things:

- **content** — I have a fresh reading and it is comfortable, so I am not bidding
- **ignorant** — I have no fresh reading, so I do not know what I am
- **failed** — my sensor has gone quiet

Sitting out is right for the first and the third. It is *not* obviously right for the second, and
the second was being reported as the third. A plant moved into the sun dries quickly; an agent that
last looked four hundred seconds ago does not know that, and "I am comfortable" is not a claim it
is entitled to make.

So this was never only a wrong log line. The belief was malformed.

# The rule is relative where the agent sets the clock

An `sensing:Subscribing` agent **chooses** the interval — that is what the capability is. So staleness
means *the sensor did not report within the interval I asked for, plus some slack*. That cannot be
a constant when the interval it sets ranges from thirty seconds to six hundred.

It is now derived: a reading is stale past **the cadence currently in force plus `sensing:readingGraceS`**,
the slack that covers a board's wake time and a late wifi association. The grace is a belief because
it is a judgement about this deployment — a board on a strong signal needs less than one at −80 dBm.

An `sensing:Listening` agent is the opposite case and keeps `sensing:maxReadingAgeS` unchanged. The device
keeps its own clock and takes no orders, so there is no interval for the agent to be relative to.
The only thing it can state is how long it is willing to wait before deciding the device has gone
quiet — which is exactly what an absolute is.

**That asymmetry is the point.** The two capabilities differ in who holds the clock, and the
freshness rule now differs the same way, instead of pretending they are the same question.

# What the log says now

The three states are distinguished, because conflating them is how a real failure gets ignored:

- content — bids, or does not, on a number it has
- ignorant — *no reading yet; cadence is Ns, last heard Ms ago* — normal, and self-correcting
- failed — *the sensor has not reported in Ns, past the cadence I set plus grace* — worth acting on

# Renaming a belief strands every agent already born

Changing `sensing:maxReadingAgeS` to `sensing:readingGraceS` is a schema change, and beliefs are written
**once at birth and never touched by start or stop**. So every agent already running held the old
term, the new code required the new one, and each refused to start:

```
fern composed sensing:Subscribing but its beliefs graph is missing sensing:readingGraceS — run orexis-validate
```

That refusal is correct — it is the self-check doing its job rather than an agent running on beliefs
it cannot interpret. But it means **there is no migration path**: the only cure is re-birth, which
discards whatever the agent had revised about itself since. On the bench that was
`podman compose down -v` and back up.

Worth knowing before renaming a belief in a world that matters. It is cheap here because nothing
yet revises its own beliefs at runtime; the day something does, this becomes a real loss and a
migration story has to exist.

# The title is literally true now: the cadence IN FORCE, acknowledged

The rule above judged freshness against the cadence the agent *commanded* — its intent, which
the board can silently fail to share: a retained command cleared from the broker (#37) leaves
the board on its compile-time default, and a firmware clamp leaves it on its own floor, while
the agent holds readings to a rhythm nobody is keeping. Since #135 the reading itself says
which cadence it was taken under — deep sleep clears the board's RAM, so the retained message
is its only memory and the ack is its only testimony — and the freshness rule prefers that
testimony over the intent. One mismatched ack is expected noise from pre-release firmware (its
live response to a reading landed in a fixed post-publish window, so the wake after every
re-aim acked the old value once — a board that waits to be *released*, #152, sleeps exactly
what it was answered, and its acks agree); the same mismatch twice running is the detector #37
never had, said in the log and drawn in the health series as `cadence_acked_s` diverging from
the commanded line. The re-send it used to have to arrange happens by itself now: every acked
reading is answered, because the answer is the release.

# The invariant underneath: a reading's instant is stamped at arrival

The boards have no clocks — no RTC, deep sleep between wakes — so a reading cannot carry its
own instant. The agent stamps it at **arrival**, and every judgment above rests on that stamp.
It is honest under exactly one assumption: **delivery is immediate**. Two natural-sounding
"reliability" changes break it silently:

- **retained readings** — an agent restarting hours later receives the broker's kept copy and
  stamps it *now*: the stale detection, the ignorance burst and the gap are all blinded at
  once, and the agent opens *calm* instead of curious, bidding on the past;
- **persistent sessions** — the broker replays the missed backlog on reconnect, each old
  reading stamped fresh at arrival, and the trend computed from replay intervals rather than
  real ones.

Losing the readings published while nobody listened is therefore a **feature**: the ignorance
burst re-fetches reality within one board-wake (bounded by the constitutional `maxSleepS`),
where the "saved" data would be a well-preserved lie. The asymmetry with the cadence command —
which IS retained, correctly — is the rule to remember: **retained is right for policy and
wrong for testimony.** A command is still true whenever the board wakes to read it; a reading
without its instant is not a fact at all. Guarded by
`test_the_agent_holds_a_clean_session` and `test_a_reading_is_never_retained`.

# Seams left open

- **Nothing nudges a returning sensor.** A device that reconnects gets its retained cadence at once
  but publishes on its own schedule, so an agent may wait a full interval for the first reading. A
  `{"sense": true}` on reconnect would close that, and requires knowing the device reconnected —
  which nothing reports today. Same root as the acknowledgement gap.
- **Grace is a fixed number, not a measurement.** An agent could learn the spread between the
  cadence it asks for and the interval it actually observes, and set its own grace from that. It
  does not; a belief is stated by the sovereign and left alone.
