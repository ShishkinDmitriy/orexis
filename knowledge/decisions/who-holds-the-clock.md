---
type: Decision
title: Sensing splits by who holds the clock — Polling, Subscribing, Listening
description: >-
  The sensing family is three capabilities on one axis: the agent asks for each reading
  (Polling, reserved), the agent states an interval the device keeps (Subscribing,
  implemented), or the device announces on its own (Listening). What was called Polling was
  Subscribing all along.
status: accepted
timestamp: 2026-08-03T18:00:00Z
---

# Amended: the three modes are named as procedures

Since [an-observation-says-how-it-was-made](an-observation-says-how-it-was-made.md) they are
spelled for what they *do*, because they are `sosa:Procedure` instances and a procedure is a
**plan** — *"a workflow, protocol, plan, algorithm, or computational method specifying how to
make an Observation."* `sosa:usedProcedure sensing:Scheduled` read as a state; it now reads as
a method.

| originally | briefly | then | now | agent capability |
|---|---|---|---|---|
| `sensing:Pull` | `PolledSampling` | `PolledSensing` | `sensing:PolledProcedure` | `sensing:Polling` |
| `sensing:Scheduled` | `ScheduledSampling` | `ScheduledSensing` | `sensing:ScheduledProcedure` | `sensing:Subscribing` |
| `sensing:Push` | `PushReporting` | `PushSensing` | `sensing:PushProcedure` | `sensing:Listening` |

Each keeps its mode word, so the pairing this record is *about* still reads at a glance. Nothing
below changed meaning; the rest of this record uses the current spelling except where it is
explicitly recounting the earlier rename.

**The `briefly` column never shipped past a review.** `Sampling` collides with `sosa:Sampling`,
an act that produces a `sosa:Sample` — a specimen taken away and examined, which is not what a
probe sitting in soil does. `Reporting` collides with `packages/orexis-capability-reporting/`, which this
project created eight commits earlier for telemetry an agent emits about itself.

**`Sensing` shipped and was superseded for a different kind of reason.** It collided with
nothing; it was SOSA's own word for what a sensor does. It went because
[a-sensor-implements-its-procedure](/decisions/a-procedure-belongs-to-whatever-performs-it.md) gave these instances a
use site where they are read aloud — `?sensor ssn:implements sensing:ScheduledProcedure` — and
there *"the sensor implements the scheduled sensing"* is a sentence about an activity, while
*"implements the scheduled procedure"* is a sentence about a plan. `ssn:implements` relates a
system to a **Procedure**, so the noun in the object position should be the one the predicate
expects. A name can be free and still be the wrong part of speech for where it ends up.

**The trade-off, stated so it is not rediscovered:** naming an instance after its class means the
name no longer says *which kind* of procedure it is — a sampling procedure or a calibration
procedure would also end in `…Procedure`, and nothing in the name would separate them. That is
real, and it costs nothing here, because the kind is carried by the qualifier class rather than
by the spelling: these three are `sensing:SenseMode` and a future calibration procedure would
not be. The shape asks for the class, never for a name that looks a certain way.

# Context

Sensing had two capabilities, `sensing:Polling` and `sensing:Listening`, derived from a device being
`sensing:PolledProcedure` or `sensing:PushProcedure`. The names described the *device*, and one of them was wrong about it.

`sensing:Polling` did not poll. A polling agent set a retained `{"sleep_s":N}` on the device's
command topic and the device woke itself on that schedule. The agent never asked for a
reading; it stated an interval and delegated the timekeeping. `sense_now()` existed and looked
like the missing half, but its own docstring called it best-effort — the ESP32 is awake for a
couple of seconds per cycle (then a fixed `CMD_WAIT_MS` window; since #152, from publish to
release) and deep-asleep the rest of the time, so a request lands on nothing unless it is
extraordinarily lucky.

So the vocabulary named an exchange the system does not perform, and hid the one it does.

# Decision — one axis, three positions

**Who holds the clock** is the axis, because it is what changes what the agent must believe —
which is the standing test for whether something deserves to be a capability.

| capability | `sensing:senseMode` (on the DEVICE, since #96) | who runs the timer | the agent states |
|---|---|---|---|
| `sensing:Polling` | `sensing:PolledProcedure` | the **agent** — it asks for each reading | an interval, its own |
| `sensing:Subscribing` | `sensing:ScheduledProcedure` | **shared** — agent sets, device keeps | an interval, the device's |
| `sensing:Listening` | `sensing:PushProcedure` | the **device** | nothing |

Strictly decreasing agent control, and each asks the agent for strictly less. What was
`sensing:Polling` is now `sensing:Subscribing`, and the mode then spelled `Pull` is now
`sensing:ScheduledProcedure` — **four spellings, and this sentence is about the first change**.
This record moved that mode's *referent* from the middle row to the top; the three renames in the
table above changed only how all three are spelled. Read `Pull` here as the name of the time, not
as today's `sensing:PolledProcedure`, which is the reserved third mode.

**"Agent sets, device keeps" was unqualified for as long as this record existed**, and a device
that cannot keep what it is given is the whole of
[#59](https://github.com/ShishkinDmitriy/orexis/issues/59). A board now states the smallest gap it
will honour and the agent cannot commit to less — see
[a-board-says-what-it-can-honour](a-board-says-what-it-can-honour.md). It does not change which
capability a sense mode grants: how a device is DRIVEN and what it can DO are different facts, and
only the first decides the family.

# Polling is declared and not built, on purpose

`sensing:Polling` is the simplest exchange there is — one request, one response, nothing retained
on a broker, no standing state anywhere — and it is what the word ought to mean. It is also
the one with the most agent control: the agent may look at a moment of its own choosing rather
than at the next moment the device happens to offer.

It cannot be had from the hardware in this world. A board that deep-sleeps between readings is
not reachable, so "ask and it replies" is not available at any price short of keeping it awake
— which costs the battery life the whole design is built around.

So the T-Box declares `sensing:Polling` and `sensing:PolledProcedure`, **no derivation rule maps one to the other**,
and no module provides it. Nothing can acquire it, and the vocabulary is honest about the
three rather than pretending there are two. Adding it later is a class and one line of
`PROVIDES` — no other package moves, because
[capability-packages](/decisions/capability-packages.md) already made that true.

# Why the middle one is not a compromise

It would be easy to read `sensing:Subscribing` as a degraded `sensing:Polling`. It is not, and the
distinction is load-bearing: **the agent has not given up deciding how often to look.** The
interval is its own belief (`sensing:fastSleepS` / `sensing:slowSleepS`), it still moves with urgency,
and it is still clamped by the constitution in three places. What is delegated is only the
*timekeeping* — a standing request instead of a repeated one — and that delegation is
precisely what buys the device its sleep.

The two levers make the same point from the other side. The interval is **retained**, so a
sleeping board receives it the instant it wakes; `sense` is **never retained** and lands only
while the board is awake between publishing and its release (#152). That inequality is not an
implementation weakness to be fixed — it is the hardware fact that makes polling and
subscribing genuinely different things to hold.

# Consequences

- **A misnamed capability stopped lying.** The firmware always implemented Subscribing; only
  the vocabulary said otherwise.
- **The reserved seam is legible.** `sensing:Polling` in the T-Box with no rule and no module is a
  statement about what this world's hardware can do, readable without reading the code.
- **The sense modes now pair one-to-one with the capabilities,** so the derivation is a lookup
  rather than a judgement, and a fourth mode would be a fourth row.

# What is still open

- **Nothing prevents declaring `sensing:PolledProcedure` on a board that sleeps.** Nothing
  checks that a device claiming to be always-reachable actually is. Today it is harmless — no
  rule reads `sensing:PolledProcedure` — and it becomes a real check the moment polling is
  built.
- **A device could support both.** Mains-powered hardware could answer requests *and* keep an
  interval; the world states one `sensing:senseMode`, so it would have to choose. Whether that
  should become a set is unanswered.

# A defect, not a seam: the command-channel guard is on the wrong premise

*(Closed by #96 and #103, and by the mode changing bearers — the account below is kept as the
anatomy of a composition failure. The mode is stated ONCE per connecting device now, a bearer
shape refuses it on anything without a connection, and a peripheral therefore cannot claim to
accept an interval at all: the escape below is unrepresentable rather than guarded against. The
device that does bear a Scheduled mode is exactly what the transport shape always targeted, so
the guard's premise and the claim's bearer finally coincide. And the runtime half is honest:
`set_cadence` reports whether anything was actually sent, and the module records nothing and
warns when it was not.)*

This record used to claim, in the bullet above, that *"the shapes require an instructable sensor
to state a command channel."* **They do not, and the sentence has been removed rather than
softened.** It is a debt with a definition of done, so it belongs in an issue; it is recorded
here only because this record asserted the opposite and a stale claim is worse than none.

Measured on `world/sensing`, removing one `mqtt:commandTopic` at a time:

| sensor | `mqtt:onBus` | world still conforms |
|---|---|---|
| `:moisture_sensor_fern` | yes | **no** — refused |
| `orexis:air_temp_fern` | no | yes |
| `orexis:air_humidity_fern` | no | yes |

The guard lives in `packages/orexis-transport-mqtt/shapes.ttl` and is conditioned on a sensor being **on a
bus**. The two DHT channels are `sosa:Sensor` and deliberately not devices — they ride the board's
topic and have no `mqtt:onBus` of their own — so the shape never targets them. Each is
`sensing:ScheduledProcedure`, each derives `sensing:Subscribing`, and each can lose the
channel an interval would arrive on without anything objecting.

**The premise is wrong, not the shape.** It asks *does this thing speak MQTT* when the question
is *does this thing claim to accept instruction* — which is a fact about the sense mode and holds
whatever the transport. That is why the hole is invisible from the transport package: the mode
that creates the obligation is not something a transport shape has any business reading.

What makes it live rather than theoretical is what happens next, and every step of it is in the
code today. `_aimed_with` returns *"a group of one — nothing is sent for it"*. The driver still
claims the sensor, because `MqttDriver.claims` is satisfied by `mqtt:readingTopic` alone. Its
`set_cadence` opens with `if sensor.command_topic:` and so returns having published nothing —
**silently, because there is nothing anomalous about it from where the driver stands**. Control
returns to `SensingModule.set_cadence`, which then unconditionally records `self.sent[key]`
and `self.sent_cadence[...]` and logs `cadence now Ns`.

So the agent ended up holding, and stating, that it set an interval the board never heard. The
board kept its flashed default forever, readings kept arriving on it, and every signal an
operator had said healthy. The silence was correct in each of the three places it occurred and
wrong in composition, which is why no single shape or function looked buggy on inspection — and
why the close is one unrepresentability plus one honest return value rather than a fourth
locally-correct check.

# Amended: the world holds the third clock (#151)

The axis gained the position it always implied. Scheduled is the agent's clock, Push is the
device's — and announce-on-crossing is the WORLD's: the device watches commanded thresholds
while it deep-sleeps (an ESP32's ULP compares the reading every second for microamps) and wakes
to speak the moment the value crosses one. The device is merely the world's messenger.

Deliberately NOT a fourth `sensing:senseMode`. The mode is who holds the HEARTBEAT, one answer
per device (#96); the alarm wake is an ADDITIONAL procedure the same device implements —
`ssn:implements sensing:AlarmProcedure`, the standard relation arriving for exactly the
reason this record kept `senseMode` ours: `ssn:implements` is wider *because* a system may
implement several procedures, and here is the second one. Held PER CHANNEL — on the sensor
whose value is watched — because which values a board can watch is a per-channel hardware
fact: an ESP32's ULP reaches the analog probe and can never speak the DHT's protocol. Since
#181 a real board's promise is ENTAILED rather than authored: the firmware class states it
(the flashed image watches unconditionally), it lands on the connecting device alone — which
is the analog channel, the DHT channels being untyped — and the wiring holds it to the
silicon, because the board's class states which pin roles its sleep-watcher reaches
(`mc:watcherReachesRole`) and `mc:WatchedChannelWiringShape` refuses a promise wired past
that reach. A stand-in still promises by hand, every channel it likes: it has no pins and no
watcher, and reporting what its world says is its constitution. A second shape requires the
implementing sensor to ride a Scheduled device with a command channel, since the bands arrive
the way the cadence does — one retained map, a band per watched pointer.

The alarm carries process control's BOTH classic limits: HI/LO (the band — desire's region
edges) and DEVIATION (`sensing:alarmDeltaFraction` of the band's width — an in-band move since
the last report that is itself the news). The board arms their intersection as one window, so
the second limit is arithmetic, not machinery. The fraction began as one figure on the
capability family and became **the agent's own revisable pick**: 0.25 was an estimate measured
on nothing, and correcting an estimate must cost a retained command, never a reflash — so a
governed agent holds it as a belief (`review:commits` grants the room, the sensing `review.rq`
re-picks it from the same evidence window as the cadence, and the two rules trade the vigil: a
lively world earns a tight cadence and a coarse delta, a still one the reverse). The family's
figure remains as the society's default and the **sentinel's bake** — a board that takes no
orders can only be flashed with the constitution, since no revision could ever reach it. What
the deviation limit measures FROM, and why slow drift belongs to the cadence rather than to it,
is its own record:
[the-alarm-answers-to-the-last-report](/decisions/the-alarm-answers-to-the-last-report.md).

> Since [the-sentinel-alarms-on-movement](/decisions/the-sentinel-alarms-on-movement.md) this
> describes the GOVERNED node only. A sentinel carries the deviation limit alone: it watches
> movement and not the range, because a board that cannot be told anything alarmed every
> patrol for as long as a pot sat outside its band.

What the promise buys, mechanically: the thresholds are the agent's region edges (desire's
`bounds`, collected like urgency), so the board literally watches its agent's desire while both
sleep; silence between heartbeats means "nothing crossed" — information — and a alarm-armed
watch counts as LIVE for #132's held claims, however long the heartbeat. The hand-watering
scenario that no cadence policy could recover — a third party's impulse inside the sleep
window — is now seen within the watch period, which was the whole of #151's argument.
