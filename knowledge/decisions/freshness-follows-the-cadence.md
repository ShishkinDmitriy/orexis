---
type: Decision
title: Freshness follows the cadence, except where the agent does not set it
description: A subscribing agent chose how long to wait between readings, so an absolute staleness limit contradicts its own instruction. Why the rule is relative for ag:Subscribing and absolute for ag:Listening, and why "I do not know" is not the same answer as "I am fine".
tags: [perception, freshness, cadence, beliefs, subscribing, listening]
timestamp: 2026-08-07T00:00:00Z
---

# The contradiction

Every agent held both of these:

```turtle
ag:slowSleepS 600       # comfortable: let the board sleep, save energy
ag:maxReadingAgeS 120   # older than this and it will not bid on the number
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

An `ag:Subscribing` agent **chooses** the interval — that is what the capability is. So staleness
means *the sensor did not report within the interval I asked for, plus some slack*. That cannot be
a constant when the interval it sets ranges from thirty seconds to six hundred.

It is now derived: a reading is stale past **the cadence currently in force plus `ag:readingGraceS`**,
the slack that covers a board's wake time and a late wifi association. The grace is a belief because
it is a judgement about this deployment — a board on a strong signal needs less than one at −80 dBm.

An `ag:Listening` agent is the opposite case and keeps `ag:maxReadingAgeS` unchanged. The device
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

Changing `ag:maxReadingAgeS` to `ag:readingGraceS` is a schema change, and beliefs are written
**once at birth and never touched by start or stop**. So every agent already running held the old
term, the new code required the new one, and each refused to start:

```
fern composed ag:Subscribing but its beliefs graph is missing ag:readingGraceS — run agora-validate
```

That refusal is correct — it is the self-check doing its job rather than an agent running on beliefs
it cannot interpret. But it means **there is no migration path**: the only cure is re-birth, which
discards whatever the agent had revised about itself since. On the bench that was
`podman compose down -v` and back up.

Worth knowing before renaming a belief in a world that matters. It is cheap here because nothing
yet revises its own beliefs at runtime; the day something does, this becomes a real loss and a
migration story has to exist.

# Seams left open

- **Nothing nudges a returning sensor.** A device that reconnects gets its retained cadence at once
  but publishes on its own schedule, so an agent may wait a full interval for the first reading. A
  `{"sense": true}` on reconnect would close that, and requires knowing the device reconnected —
  which nothing reports today. Same root as the acknowledgement gap.
- **Grace is a fixed number, not a measurement.** An agent could learn the spread between the
  cadence it asks for and the interval it actually observes, and set its own grace from that. It
  does not; a belief is stated by the sovereign and left alone.
