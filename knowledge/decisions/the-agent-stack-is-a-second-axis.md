---
type: Decision
title: The agent stack is a second axis, and the transport has no place on the first
description: >-
  Cognitive layering and the agent stack are two orthogonal decompositions, and confusing them
  is what puts a broker in a diagram of the mind. Decided that the stack is sliced by
  REPRESENTATION — network, transport, translation, the belief-revision seam, mind — that the
  cognitive layers partition only the top box, that an infrastructure failure becomes a belief
  only by explicit modelling and never by leaking upward, and that a message from another agent
  takes a different path through translation than a reading does, because a speech act is not
  an observation.
status: accepted
timestamp: 2026-08-26T18:00:00Z
---

# What was true before

[layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)
named the cognitive layers — reactive, progression, deliberation — and left an obvious question
unanswered: where is MQTT on that table? The honest answer is nowhere, and the reason is that
it is not the same decomposition. The tree has always had both and named only one, which is how
a diagram ends up with a broker sitting next to a planner.

# What is decided

**Two axes, orthogonal.** The first is cognitive layering, sliced by timescale and
interruptibility. The second is the **agent stack**, sliced by representation: bytes, then
grounded symbols, then beliefs. The transport lives on the second and has no position on the
first at all.

```
mind          plans, intentions, deliberation      ← axis 1 partitions this box
─────────────────────────────────────────────      symbols only
BRF           what counts as a belief change
translation   channel -> predicate, validate, timestamp, dedupe
transport     the link: client, QoS, retained, credentials
network       broker, TCP, wifi
```

The classic name for the whole of axis 2 below the mind is the agent's **perceptual and
effectoric interface** — Jason calls it the environment, JADE the message transport service —
and in both it is deliberately outside the interpreter. It is outside ours too: the
[transport](/domain/transport.md) is a capability the fact of a bus grants
([the-kernel-has-no-mailbox](/decisions/the-kernel-has-no-mailbox.md)), and the kernel never
learns what a channel is carried over.

**The BRF row is the seam where the axes meet.** Everything above it is symbolic and
cognitively layered; everything below is bytes and has no cognitive role. That is the same seam
[layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)
calls the interface, seen from the other side.

**Infrastructure failures are not beliefs.** A broker unreachable, a certificate expired, a
malformed payload, a duplicate delivery — none of them is a fact about the world, and none may
reach a plan as one. They are handled where they happen, with retries and a bound. Their only
cognitive projection is a belief somebody **deliberately modelled**, minted at the translation
boundary. The rule: *an infrastructure failure becomes a belief only by explicit modelling,
never by leaking upward as an exception.*

**A message is not an observation.** Our agent bus is the same MQTT as our sensor bus, and that
is a deployment fact, not a semantic one. A reading is an observation about the world; a bid, an
offer, a claim is a **speech act** — it has a performative and a sender, and what it changes is
what this agent is owed, owes, or may do, never what the world is. The two take different paths
through translation, and keeping them distinct is cheap now and painful to undo later.

# What is already true of the code

- **Transport**: `packages/orexis-transport-mqtt/` — the client, the credential, the session, the
  watchdog. Nothing above it names a broker.
- **Translation**: sensing's `codec`, `scaling` and `pointer` turn a payload into a number, and
  `sensed_writer` stamps it with its instant and its instrument and upserts one node per
  (subject, property) — validate, timestamp, dedupe, in that order, exactly the row's job.
- **The two paths are already distinct, in fact if not in name.** Sensing's path ends in a
  `sosa:Observation` in the state graph. The market's path ends in a `market:Round` in the
  agent's own beliefs, a claim satisfying an [intention](/domain/intention.md), or an
  [obligation](/domain/obligation.md) on the ledger — never an observation. A bid's sender is
  the topic segment it arrived on and its signature, checked before anything is believed.
- **One projection exists and is deliberate**: a sensor that stops delivering does not raise —
  its freshness want goes cold, which is a belief the agent can plan about
  ([the-region-want-is-sensings-want](/decisions/the-region-want-is-sensings-want.md)). A broker that goes
  away projects to nothing at all: the watchdog resigns the process
  ([a-dead-session-is-resigned-not-endured](/decisions/a-dead-session-is-resigned-not-endured.md)),
  which is the honest answer for a fault the agent cannot reason about from inside.

# What this makes testable

The mind can be exercised with a **stub environment** — grounded predicates fed straight in, no
broker — and that is where most plan-logic tests belong. `tests/conftest.py` already builds an
agent whose transport client is captured, so `deliver(channel, payload)` is the environment
speaking; nothing in the suite needs a broker except `infra/tests`, which is a contract with the
infrastructure rather than with the code.

# Seams left open

- **The speech-act path has no vocabulary.** A message's performative and sender are implicit —
  the topic it arrived on, the signature it carries — and nothing refuses an observation minted
  from a peer's message. Filed as [#394](https://github.com/ShishkinDmitriy/orexis/issues/394).
- ~~**The BRF is implicit.**~~ In 0.1.0, `packages/orexis-agent-deliberation/reviser.py` is the row: every reactive path marks a
  want there and the pass runs on the mind's own thread (#392). What it DECIDES is still thin —
  dedupe by want, and nothing else — but where it decides is one place now. In Agent 0.2.0 the
  row is `agent/belief/`: a change is written as any belief is, and the rules conclude its
  [revisions](/domain/revision.md) beside it. What it decides is
  nothing — any belief is accepted — and that is the decision.
- **`sensor_unreachable(...)` is not modelled.** The freshness want covers not-knowing, which is
  what a planner can act on; whether the DISTINCTION between a quiet board and a dead link is
  worth a belief of its own is open, and `quiet()` says it in logs today.
