---
type: Decision
title: Perception splits by who holds the clock — Polling, Subscribing, Listening
description: The perception family is three capabilities on one axis: the agent asks for each reading (Polling, reserved), the agent states an interval the device keeps (Subscribing, implemented), or the device announces on its own (Listening). What was called Polling was Subscribing all along.
status: accepted
stage: v1
tags: [sensing, capabilities, firmware, ontology, naming]
timestamp: 2026-08-03T18:00:00Z
---

# Context

Perception had two capabilities, `perception:Polling` and `perception:Listening`, derived from a device being
`perception:Pull` or `perception:Push`. The names described the *device*, and one of them was wrong about it.

`perception:Polling` did not poll. A polling agent set a retained `{"sleep_s":N}` on the device's
command topic and the device woke itself on that schedule. The agent never asked for a
reading; it stated an interval and delegated the timekeeping. `sense_now()` existed and looked
like the missing half, but its own docstring called it best-effort — the ESP32 is awake for
`CMD_WAIT_MS` (1.5s) per cycle and deep-asleep the rest of the time, so a request lands on
nothing unless it is extraordinarily lucky.

So the vocabulary named an exchange the system does not perform, and hid the one it does.

# Decision — one axis, three positions

**Who holds the clock** is the axis, because it is what changes what the agent must believe —
which is the standing test for whether something deserves to be a capability.

| capability | `perception:senseMode` | who runs the timer | the agent states |
|---|---|---|---|
| `perception:Polling` | `perception:Pull` | the **agent** — it asks for each reading | an interval, its own |
| `perception:Subscribing` | `perception:Scheduled` | **shared** — agent sets, device keeps | an interval, the device's |
| `perception:Listening` | `perception:Push` | the **device** | nothing |

Strictly decreasing agent control, and each asks the agent for strictly less. What was
`perception:Polling` is now `perception:Subscribing`, and `perception:Pull` is now `perception:Scheduled`.

# Polling is declared and not built, on purpose

`perception:Polling` is the simplest exchange there is — one request, one response, nothing retained
on a broker, no standing state anywhere — and it is what the word ought to mean. It is also
the one with the most agent control: the agent may look at a moment of its own choosing rather
than at the next moment the device happens to offer.

It cannot be had from the hardware in this world. A board that deep-sleeps between readings is
not reachable, so "ask and it replies" is not available at any price short of keeping it awake
— which costs the battery life the whole design is built around.

So the T-Box declares `perception:Polling` and `perception:Pull`, **no derivation rule maps one to the other**,
and no module provides it. Nothing can acquire it, and the vocabulary is honest about the
three rather than pretending there are two. Adding it later is a class and one line of
`PROVIDES` — no other package moves, because
[capability-packages](/decisions/capability-packages.md) already made that true.

# Why the middle one is not a compromise

It would be easy to read `perception:Subscribing` as a degraded `perception:Polling`. It is not, and the
distinction is load-bearing: **the agent has not given up deciding how often to look.** The
interval is its own belief (`perception:fastSleepS` / `perception:slowSleepS`), it still moves with urgency,
and it is still clamped by the constitution in three places. What is delegated is only the
*timekeeping* — a standing request instead of a repeated one — and that delegation is
precisely what buys the device its sleep.

The two levers make the same point from the other side. The interval is **retained**, so a
sleeping board receives it the instant it wakes; `sense` is **never retained** and lands only
inside the waking window. That inequality is not an implementation weakness to be fixed — it
is the hardware fact that makes polling and subscribing genuinely different things to hold.

# Consequences

- **A misnamed capability stopped lying.** The firmware always implemented Subscribing; only
  the vocabulary said otherwise.
- **The reserved seam is legible.** `perception:Polling` in the T-Box with no rule and no module is a
  statement about what this world's hardware can do, readable without reading the code.
- **The sense modes now pair one-to-one with the capabilities,** so the derivation is a lookup
  rather than a judgement, and a fourth mode would be a fourth row.

# What is still open

- **Nothing prevents declaring `perception:Pull` on a board that sleeps.** The shapes require an
  instructable sensor to state a command channel, but nothing checks that a device claiming to
  be always-reachable actually is. Today it is harmless — no rule reads `perception:Pull` — and it
  becomes a real check the moment polling is built.
- **A device could support both.** Mains-powered hardware could answer requests *and* keep an
  interval; the world states one `perception:senseMode`, so it would have to choose. Whether that
  should become a set is unanswered.
