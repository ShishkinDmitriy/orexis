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
  nobody had. The binary codec is left open with three candidates weighed — Kaitai, CBOR and
  Zserio — because what separates them is which side of the wire gets generated, and the board
  is the side that writes. Either way the guard is a round-trip test, not a generator.
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

# Which codec — three candidates, and the axis that separates them

Deliberately not settled here, because the sequencing above says the codec comes last and because
this section has now been rewritten three times on facts about dependencies rather than on
anything about this project. What is settled is the QUESTION to ask, which is not "which format is
most compact" but **which side of the wire gets generated**.

The board writes and the agent reads. So what matters is whether a schema produces a C++ *writer*,
and the answer is not what the marketing implies for any of them.

| | C++ writer generated | Python reader generated | bit packing | evidence |
|---|---|---|---|---|
| **Kaitai Struct** | **no** | yes | yes | its C++ runtime has 25 `read_*` and **0** `write_*`; serialization is Java and Python only |
| **CBOR** | n/a — hand-written | n/a — generic decoder | no, byte-aligned | a decoder is a pip install; nothing is generated either way |
| **Zserio** | **yes** | yes | yes, plus delta-packed arrays | its `BitStreamWriter.h` has 25 `write*` methods |

**Kaitai is language-neutral for PARSING** — twelve targets including C++/STL, and its user guide
describes `ksc` as translating a spec "into parsing libraries". Its serialization is a later,
partial rollout: Java and Python today, others promised, and no work in flight on the C++ runtime.
So for the direction this change needs it generates the half that was cheap anyway. **It inverts
for a command channel** — agent serialises in Python, board parses in generated C++, both ends
generated, nothing missing. The governed node has exactly that channel, and whoever reaches for a
binary command format should start there rather than re-deriving this table.

**CBOR is the least machinery for the least benefit.** No code generation, no build step, and it
decodes to exactly the maps and arrays a pointer already walks, so the pointer stage does not move
at all. It is also byte-aligned and self-describing, so it is the largest of the three on the wire
— about twelve bytes an event against eight hand-packed.

**Zserio is the one built for this shape.** It is a serialization framework rather than a parser
generator, so writing was never an afterthought; it emits C++ and Python from one schema; and its
**packed arrays apply delta compression to integer elements**, which is close to ideal for a ring
of clustered readings with marching timestamps. Its C++ generator targets C++11 with allocator and
polymorphic-allocator support and an explicit functional-safety section — a runtime written by
people shipping into embedded, not a desktop library being squeezed onto one.

# What is not known, and would decide it

Three measurements, none of them arguments, and the reason no choice is recorded:

- **Flash cost of the Zserio runtime plus generated code**, against a firmware already at 72%. This
  is the one that could plausibly rule it out, and it is an hour's work rather than a debate.
- **Exception behaviour on Arduino-ESP32.** Zserio documents exception handling under functional
  safety; the Arduino core's settings vary. A compile test answers it early.
- **Whether the wire shape has stopped moving.** Choosing a codec for a format still being designed
  is optimising the wrong thing, which is why this is step three and not step one.

# The guard is a test, whichever wins

The part worth more than the choice. Only Zserio generates both halves; with Kaitai or CBOR a
hand-packed encoder can silently disagree with its decoder, and the two copies sit on opposite
sides of a radio and a reflash. What catches that is a round trip — capture a real payload off the
device, parse it with the agent's own decoder, assert the fields. It costs a test rather than a
toolchain, works whatever the encoding, and is the thing to build first even if the codec is never
chosen.

# A note on how this section was arrived at

Recorded because the process was more instructive than the conclusion. Three codecs were
recommended in one evening, and the first two recommendations each fell to a fact about the
dependency — not to a change of mind about the design. Kaitai was argued for on "one schema
generates both parsers", which is false for C++ and was checkable in a minute by counting methods
in its runtime header. CBOR was then argued for absolutely, which overcorrected past a real case
(the command direction) where Kaitai wins outright.

**The general lesson: for a dependency, check the artifact rather than the claim.** The runtime
headers settled in two commands what the documentation, the marketing page and three rounds of
reasoning could not.

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
