---
type: Decision
title: An undelivered crossing is a lie told by silence
description: >-
  A sentinel's silence is information only while it means nothing crossed. When the radio
  cannot reach the broker, an excursion that goes out and comes back is erased entirely — the
  society sees a flat line across the exact interval the alarm exists to report. So undelivered
  CROSSINGS are retained and flushed on the next successful connect. Alarms and not readings,
  because an alarm is rare by construction and a heartbeat backlog is unbounded and mostly
  redundant. Backfill must stay distinguishable from live, or the history claims knowledge
  nobody had. The binary codec, when it comes, is CBOR and not Kaitai — correcting this record's
  own first answer, since Kaitai emits no C++ writer and so leaves the layout declared twice
  regardless.
status: accepted
timestamp: 2026-08-24T00:40:00Z
---

# An undelivered crossing is a lie told by silence

The sentinel's central claim, stated in its README and relied on by every generous heartbeat, is
that **silence means nothing crossed**. That is what moves freshness work off the radio and onto
the coprocessor, and it is why a thirty-minute beat is safe where a twelve-minute polling rule
would not be.

It holds only while the board can speak when it needs to.

# What the bench showed

WiFi failed for six minutes. In that window the value went from 0.15 to 1.00 and back. The board
saw all of it — it looks every fifteen seconds — and the society saw **nothing**: a flat line
across precisely the interval the alarm exists to report.

That is not a gap in the record. It is the record asserting that nothing happened, at the one
moment when something did. Losing two heartbeats of drift is tolerable and was tolerated; losing a
round trip is the alarm's whole promise failing, silently, in the way that leaves no trace to
notice later.

The distinction is the decision: **silence is information when it means "nothing crossed", and a
falsehood when it means "something crossed and I could not tell you".** Nothing on the wire
separates those two today.

# The decision — retain crossings, not readings

Undelivered **alarms** are held in RTC memory and flushed on the next successful connect. Each
keeps its own value, its own prior quiet sample (see
[the-sentinel-alarms-on-movement](/decisions/the-sentinel-alarms-on-movement.md)) and its own
instant.

**Alarms and not readings**, and the difference is what makes this small enough to build. A backlog
of every missed heartbeat is unbounded, mostly redundant — the next beat carries the drifted value
anyway — and grows with the outage. A crossing is rare *by construction*: it is news, it is what
the persistence counter exists to make rare, and a two-hour outage produces a handful. Sixteen
slots at about a dozen bytes each is a couple of hundred bytes of a memory that has kilobytes
spare.

It also keeps the semantics already built. A crossing that arrives late is still a crossing with a
corner; a backfilled heartbeat would be a value with no story, and folding both into one mechanism
would cost `prev` the meaning it was added for.

# Backfill must be distinguishable from live

The point on which this can go wrong. A retained alarm carries the instant it *happened*, not the
instant it arrived, or the corner lands in the wrong place and the fix has recreated the defect it
was built for. But a series where backfilled points are indistinguishable from live ones is a
history that claims knowledge the society never had — a query asking "when was this agent flying
blind?" would get a clean answer and a false one.

SOSA already has the split and `agent/observation.py` already carries both instants: the value's
own `phenomenonTime`, and the `resultTime` at which it reached anyone. A late crossing states both
and they differ. Nothing else has to change to make an outage findable afterwards.

Two consequences worth stating before someone meets them:

- **A flushed batch must not re-anchor freshness as though it were live.** The agent legitimately
  heard from the board just now; it did not legitimately learn that the reading is current. Those
  are different facts and a `maxReadingAgeS` rule that conflates them will call a healthy board
  fresh on the strength of a two-hour-old value.
- **A late alarm is not a reason to act.** It reports a crossing that has already been superseded
  by the live reading in the same flush. Deliberation belongs to the newest value; the older ones
  are history being filled in.

# Sequencing, and why the codec comes last

Three separable pieces, and the order is the argument:

1. **Retention** — the ring in RTC memory, flushed on connect. The part with real unknowns, because
   only a real outage tests it.
2. **A payload carrying several.** In JSON that is roughly 1.2 KB for sixteen, and PubSubClient's
   default ceiling is 256 bytes — of which the topic and the present payload already spend ~235.
   `setBufferSize()` lifts it. Bloated over a battery radio, where airtime is the cost, but correct.
3. **A binary codec.** Sixteen events packed is ~180 bytes: inside the default ceiling, and less
   airtime is directly less battery.

1 and 2 ship together; 3 arrives later **without touching either**, which is exactly what the codec
family was built to allow and would incidentally demonstrate the interchangeability
[bytes-become-a-quantity-in-stages](/decisions/bytes-become-a-quantity-in-stages.md) admits is
currently asserted rather than shown. Building the codec first would be optimising a wire format
that is still moving.

# CBOR rather than Kaitai, and the reasoning that first said otherwise

This section argued for Kaitai and was wrong, on a fact worth recording because it is the kind
that sounds right: **a `.ksy` is one declaration, and the compiler generates both parsers from
it.** It does not. Kaitai's serialization support is Java and Python only — there is no C++
writer, and the ESP32 is the side doing the writing.

So what Kaitai would actually give is a generated Python *reader* and a hand-written C++ *packer*
that must match it: still two declarations of one layout, on opposite sides of a radio and a
reflash, drifting the first time a width changes. That was the entire argument for preferring it,
and it survives only half.

Two further costs, glossed the first time. `kaitai-struct-compiler` is a JVM tool, which is real
weight in a repository whose gates are `pytest` and a shell script and which wants CI
([#47](https://github.com/ShishkinDmitriy/orexis/issues/47)). And the size advantage is narrower
than it sounds: for `[value, prior, instant]`, CBOR with arrays is about twelve bytes an event
against eight packed, so sixteen events is 192 bytes against 128 — **both inside PubSubClient's
256-byte default**, which means the packet ceiling does not decide it either.

**So `codec:Cbor`**, which is what [bytes-become-a-quantity-in-stages](/decisions/bytes-become-a-quantity-in-stages.md)
already called the cheapest proof: a pip install, no code generation, no JVM, and it decodes to
exactly the maps and arrays a pointer already walks, so the pointer stage does not move at all.

**And the drift is guarded by a test, not by a generator.** Neither codec emits a C++ writer, so
both leave a hand-packed encoder that can disagree with its decoder. What catches that is a
round-trip: capture a real payload off the device, parse it with the agent's own decoder, assert
the fields. That is worth more than the code generation was ever going to buy, works whatever the
encoding, and is the guard that should have been proposed in the first place.

`codec:Kaitai` stays declared and unimplemented. Its comment is still right about the design — a
spec yields a tree and no other stage moves — and it remains the correct answer for a device
speaking a protocol somebody else defined, where the layout is a given rather than ours to choose.
It is the wrong answer for a format we author on both ends.

# Seams left open

- **What to drop when the ring is full**, and the obvious answer is wrong. Dropping the oldest loses
  the beginning of an excursion, which is the corner; dropping the newest loses where it ended up.
  What a reader most wants out of a long outage is probably the ENVELOPE — the extremes and the
  ends — rather than a fair sample of the middle, and no mechanism here computes that.
- **The governed node has the same hole**, and worse: it is commanded, so a failed publish also
  leaves its agent's cadence unacknowledged. Nothing here addresses it.
- **Nothing tests any of it against real loss.** The failure mode only appears when a radio fails
  in a specific window, which no test in this repository can produce. It will be verified by
  breaking the WiFi on purpose, which is not the same as a guard.
- **Retention is not durability.** RTC memory survives deep sleep and not a power cut, so a battery
  change during an outage still erases the excursion. Making that survive would mean flash, wear
  levelling, and a different decision.
