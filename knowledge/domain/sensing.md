---
type: Capability
title: Sensing — sensing as the agent's initiative
term: http://example.org/orexis/sensing#SensingCapability
description: Sensing splits by who holds the clock — Polling (the agent asks each time, reserved), Subscribing (the agent states an interval, the device keeps it), Listening (the device announces). The agent owns when it looks, the board owns what it reads.
---

**An agent may hold several sensors, and two combinations are broken.** Different properties on
one subject destroy each other's record, and mixed sense modes leave one sensor's cadence
un-aimed. Both are triggered by giving a subject a second kind of sensor — see
[one-agent-many-sensors](/decisions/one-agent-many-sensors.md).

# What it is

Sensing, in **capabilities decided by the hardware** and derived at genesis (see
[capability-packages](/decisions/capability-packages.md)). The axis is **who holds the
clock**, and it is the axis because it is what changes what the agent must believe:

| capability | device (`sensing:senseMode`) | who runs the timer | the agent states |
|---|---|---|---|
| **`sensing:Polling`** | `sensing:PolledProcedure` | the **agent** — it asks for each reading | an interval, its own |
| **`sensing:Subscribing`** | `sensing:ScheduledProcedure` | **shared** — the agent sets it, the device keeps it | an interval, the device's |
| **`sensing:Listening`** | `sensing:PushProcedure` | the **device** | nothing |

Strictly decreasing agent control, and each asks the agent for strictly less.

**`sensing:Polling` is reserved, not built.** It is the simplest exchange — one request, one
response, nothing retained anywhere — and it is what "polling" ought to mean. It needs a
device that is reachable at any moment, and a board that deep-sleeps between readings is not
that: the request lands on nothing. So the vocabulary declares it, no derivation rule grants
it, and no module provides it. Adding it is a class and one line of `PROVIDES`.

**`sensing:Subscribing` is what the ESP32 firmware does today**, and the distinction is worth
keeping sharp: the agent has not given up deciding *how often* to look — only the
timekeeping. A standing request instead of a repeated one is what buys the device its sleep.

Which one an agent gets is not an opinion anyone holds: it follows from `sensing:senseMode` on the
device it is wired to. Reflash the board, re-run genesis, and the capability changes with it.
This is the sensing face of
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md).

# The contract

```
agent -> board   mqtt:commandTopic   {"sleep_s":N,"band":"LOW"} (retained) | {"sense":true}
board -> agent   mqtt:readingTopic   {"value":0.183,"sensor":"...","sleep_s":600,
                                    "temperature":21.4,"humidity":0.463}
agent -> peers   mqtt:eventTopic     {"agent":...,"property":...,"value":...,"band":"LOW"}
```

Every one of those channels is **stated in the world graph** on the resource that owns it —
nothing builds a topic from a naming convention, so renaming a channel is a genesis edit. Each
topic also **derives an `mqtt:Channel`**, one node per distinct string, so a [channel](/domain/channel.md) is a thing
rather than a literal and two devices naming one topic are visibly on one channel rather than
coincidentally alike. That is what carries the encoding — see
[a-stream-is-a-thing](/decisions/a-stream-is-a-thing.md). The
broker they are on is stated there too, as an `mqtt:MessageBus`: a channel name means nothing
without it, and members who disagree about the bus are not one society.

**One board publishes ONE message, however many peripherals it carries.** A board is one MQTT
client with one credential, so a second channel would mean a second principal. Which value in
that message belongs to which sensor is stated per sensor, as an `mqtt:readingPointer` — a JSON
Pointer, `/temperature`. Absent means `/value`, which is what every single-property board
already sends, so most sensors state nothing. A device reporting two properties is therefore
**two sensors sharing a reading topic**, not one sensor with two properties, and a field that
is absent is recorded by nobody rather than defaulted to zero. See
[a-reading-is-one-value-so-it-is-pointed-at](/decisions/a-reading-is-one-value-so-it-is-pointed-at.md).

A cadence goes the other way and is the **board's**, not a property's: one device sleeps once,
so the sensors sharing a command topic are aimed together and the tightest interval any of
them asks for wins.

**The board is a `sosa:Platform` and an `ssn:System`**, and the two say different things about
it. As a Platform it *hosts* its parts; as a System it *does* things — it holds the credential
and publishes, and it keeps the clock. A part is the other way round: an `ssn:System` with its
channels as `ssn:hasSubSystem`, and not a Platform, because nothing is mounted on a KY-015. That
chain is what ties `air_temp_fern` and `air_humidity_fern` to the part they read, and what makes
"what else is on this board" a query rather than a comparison of topic strings. The wiring says
the same thing as `mc:carries`, which is a subproperty of `sosa:hosts`; the society states it in
SOSA's terms because an agent is never handed the wiring. See
[a-board-is-a-platform](/decisions/a-board-is-a-platform.md) and
[a-procedure-belongs-to-whatever-performs-it](/decisions/a-procedure-belongs-to-whatever-performs-it.md).

Being on one board is what *permits* one message — not what causes it. SSN says nothing about
how observations are transmitted, so the topics decide that and the hosting only tells you what
could have shared one.

**What causes it, for a DHT11, is the part.** It answers one request with one frame carrying
both values, produced by the same sampling, and cannot be asked for temperature alone — so those
two are simultaneous by construction and the message is a single measurement rather than a
convenient batch. The distinction has teeth: read as a batch, each value was stamped as it was
written and one physical read left three instants in the record.

**A world that runs does this now**, rather than a world that is described doing it.
`world/simulation` states a stand-in reporting soil moisture and air temperature down one wire,
and bringing it up produces `{"sensor": "sensor_fern", "temperature": 21.15, "value": 0.39}` on
the broker and two observations from it — one per sensor, each with its own property and its own
unit. Until that existed, every claim on this page below the wire was argued in fixtures: the
real firmware sends three values and has never been compiled here, and the stand-in sent one. See
[a-stand-in-reports-what-its-world-says-it-does](/decisions/a-stand-in-reports-what-its-world-says-it-does.md).

**A reading becomes a number in three stages**, and each is a fact about the binding rather than
about the agent watching it:

```
bytes ──[codec]──▶ document ──[pointer]──▶ raw value ──[scaling]──▶ quantity
```

The pointer above is the middle one. The outer two are families with interchangeable members —
`packages/codec/` and `packages/scaling/` — and which member serves a reading is **derived at
genesis**, from what a world states or from its silence, exactly as `sensing:Subscribing` is derived
onto an agent from `sensing:senseMode`. They land on different bearers, because they are facts about
different things: the **scaling** is the sensor's, since a curve is a property of the probe, and
the **codec** is the **[channel](/domain/channel.md)'s**, since one topic carries one format however many sensors read
out of it. A sensor reaches its codec through the channel it publishes on. Every sensor here gets `codec:Json`
and `scaling:Identity`, and neither is a placeholder: the boards send JSON, and they scale
their counts before publishing, so the calibration that remains genuinely is the identity
function.

The calibration is also where a number acquires a **unit**. Soil moisture `0.183` and air
humidity `0.46` are both dimensionless fractions and look identical; air temperature `21.4` is
degrees Celsius. `scaling:quantityUnit` states which, as a QUDT IRI. See
[bytes-become-a-quantity-in-stages](/decisions/bytes-become-a-quantity-in-stages.md).
ingest path and nothing downstream can tell them apart.

Note what goes out on the event topic: the agent's **own verdict**, not its raw state. That is
voluntary disclosure — a host learns that scarcity has appeared without ever reading anyone's
moisture.

# Two levers, deliberately unequal

- **Interval** (`sleep_s`) is *standing policy*, published **retained**. A board that is deep
  asleep now still receives it the instant it wakes and subscribes. This is the reliable
  lever, and the real one: to see sooner, tighten it. Only a subscribing agent has it.

  It is a **sleep duration, not a period.** The observed gap between readings is `sleep_s`
  plus whatever the wake costs — boot, WiFi association, broker connect — which on an ESP32
  is several seconds and occasionally much more. A 10s sleep is measured at ~19s between
  readings. That gap is not drift to be corrected: the agent is choosing how long the device
  may rest, and the device honours exactly that. Anything tighter than the wake cost is
  mostly wake cost, which is why the constitutional floor sits where it does.
- **The bands** ([band](/domain/band.md) edges, as a `watch` map of `pointer -> [low, high]`) arm the crossing-watchers (#151),
  one per channel the world says is watched (`ssn:implements sensing:AlarmProcedure`, on
  the SENSOR — per channel, because which values a board can watch is a per-channel hardware
  fact: an ESP32's ULP reaches the analog probe and never the DHT, where a stand-in may watch
  everything it has). The bands are the agent's region edges, retained beside the cadence, and
  the board wakes off-cadence the moment ANY watched value leaves it — the reading then
  says `"wake":"alarm"`, the one arrival that means the world changed rather than the clock
  ticked. Silence from a watched channel means "nothing crossed", which is information; a
  plain scheduled board's silence means only "not due yet".
- **Sense** (`sense:true`) is a *best-effort nudge* — it lands only if the board happens to be
  awake between publishing and being released, and is **never retained** (a retained `sense`
  would re-fire on every wake, forever).

**The wake ends with a release, not a timer (#152).** After publishing, the board waits for
the agent's answer to *that reading* — the agent answers every one, and the answer carries the
cadence — and sleeps the moment it lands, usually tens of milliseconds later. A fixed listen
window used to be idled out in full every wake; now the timeout is only the fallback for an
agent that is down, in which case the board says so and sleeps on the retained command it
drained before publishing. The reply being guaranteed is also what makes the ack exact: a
releasing board sleeps precisely what it was answered, so its next reading receipts the
cadence actually kept.

# The band rides the same message, and gets the retention for free

A [band](/domain/band.md) travels on the command topic beside `sleep_s`, for a device that can
display it — a status LED. It is not a third lever and the board never acts on it.

It goes here rather than on a topic of its own for the reason a control topic was never added
either: **the channel already exists, the board is already subscribed, and the ACL already
grants it.** A second topic would need its own grant, its own retained slot, and would arrive
at a different moment from the cadence it belongs with.

Retention is what makes it work at all. A board that deep-sleeps learns the current verdict the
instant it subscribes, instead of showing the state before last until it happens to take
another reading.

**One consequence caught the dedup.** The cadence was only re-sent when the interval changed,
which is correct for an interval and wrong once anything travels with it: a pot drying from OK
to LOW *inside one cadence band* would have kept the old colour indefinitely — the state most
worth seeing, displayed as the state before it. The comparison is now the whole message.

The verdict is collected the way every cross-capability opinion is, through the [choir](/domain/choir.md) — whose
answer it is, and why an agent with no stake has none to give, is [band](/domain/band.md)'s. What
matters here is that this capability passes it on without reading it, and the transport driver
below never learns what one is.

The unequal pair is the whole reason `sensing:Polling` is a separate capability rather than a mode
of this one. `sense` is what polling would be built on, and its unreliability here is not an
implementation weakness — it is the hardware fact that makes the two genuinely different
things to hold.

# Capability vs binding — what varies, and what does not

The capabilities above say what an agent must **decide**. How a device is actually spoken to
is a separate axis, and deliberately not part of the capability: a scheduled board on a bus
and one on a GPIO pin present the same choices and the same obligations, and differ only in
the driver that carries the message.

So the protocol lives on the **device** (`mqtt:onBus` plus its channels), a `Driver` is selected
per sensor from what the device declares, and the agent's attention policy is untouched by
any of it. The test for whether something belongs in a capability is whether it changes what
the agent must believe: who holds the clock does (an interval, or none), MQTT-vs-HTTP does
not. An
agent can hold one sensor on a bus and another on a wire under a single policy — which is
exactly what naming the transport in the capability would have made impossible.

Adding a transport is therefore small: a driver, its terms, and its completeness rules. No
new capability, no belief changes.

# It declares how an observation-backed want is measured

Since [a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md), this
package's `measures.ttl` states the [urgency](/domain/urgency.md) measure for any want about a
`sosa:ObservableProperty` (`ag:measureOf`): a reading against the [aim](/domain/aim.md),
scaled by the survival room on the side the value sits. Sensing's, because the reading is its
whole subject — the sovereign's split puts the mind's structure in the kernel and how badness
is weighed with the capability that owns the question, exactly as an effect rule's content is
the lever-owner's. The kernel evaluates the declared text (`agent/measure.py`) and never knows
it; the choir `urgency` hook below is the same contribution asked live.

# Cadence is desire-relative, like the band

Attention scales with how close the plant is to its own `LOW`: thirsty plants watch closely,
comfortable ones let the board sleep. The numbers are **the agent's own belief**
(`sensing:fastSleepS` / `sensing:slowSleepS` in `:beliefs/<agent>`), read at startup — a succulent can
reasonably watch less often than a fern, and does. The policy that turns them into an interval
lives with the agent (`cadence_for`), never on the board — same reason the band does. A
polling agent would read the same two figures: they describe an interval either way, and only
whose timer runs it changes.

**Ignorance is urgent** (#137), for the reason [desire](/domain/desire.md) gives — ask the
choir `urgency` with no value and the question becomes *how urgent is not knowing*. What sensing
does about it is the part that belongs here: `start()` aims every sensor at once instead
of waiting for a first reading to trigger the computation: at birth — a desired state, an empty
sensed graph, maximum uncertainty — the board opens at the fast end, gathers the readings that
end the ignorance and establish a trend, and relaxes through the same recomputation every
reading triggers. Two forces, finding their equilibrium: the need to know presses toward the
fast end, the cost of looking holds the slow end, and the cadence is where they meet. An agent
with no stake opens at its own slow pace — the burst is desire's answer, not a boot ritual.

**And no longer than the trend allows** (#133). Urgency answers where the state *is*; a sleep
granted on that alone can begin moments before the trend crosses into trouble, and nobody hears
for the whole window. So the candidate sleep is checked against where the state is *heading*:
the slope over the last two readings predicts the value at the end of the sleep, the same
stakeholder is asked how urgent *that* would be, and a worse answer earns its own, shorter
cadence. Tighten-only — a favourable trend relaxes nothing, because a prediction is trusted
only in the direction where being wrong costs a reading rather than a plant. The slope is
module memory (the store upserts observations, so history for it survives nowhere else), dies
with the process, and is rebuilt from the next two readings; until then the bound simply is
not there. Attention follows not just where you are but where you are going — the
[derivative principle](/decisions/control-the-derivative-not-the-value.md), one level down.

**The comfortable end is a pick, not a constant.** `sensing:slowSleepS` is what its author chose
before the agent had seen a reading; an agent that watches a probe report the same value for a
window may re-pick it, inside the room its world's `review:commits` leaves it — and must come back the
moment the readings move again. Only the comfortable end, so a thirsty plant is still watched at
`sensing:fastSleepS` whatever a review concluded: desire-relative is the first thing and this is the
second. A reading that never changes **at all** argues for *tightening*, because an instrument
that has not moved to the last bit is likelier broken than the world it measures is perfectly
still. See [a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md).

Bounds (`MIN_SLEEP_S` / `MAX_SLEEP_S`) are **constitutional** and enforced in *three* places:
the SHACL shapes reject beliefs that exceed them, the agent clamps, and the firmware clamps
again on receipt. Autonomy over attention, never the freedom to sleep through a drought.

# Cadence ≠ content — why agent-chosen timing stays honest

Handing the agent the timing does **not** hand it the number. It chooses *when* to look; the
sensor still authors *what* it reads. Two guards close the gap that agent-chosen timing
opens, and they apply equally to polling and subscribing:

- **Freshness** — a bid must cite a reading no older than the agent's own `sensing:maxReadingAgeS`;
  a stale reading means the agent **sits the round out** rather than bidding on a comfortable
  old number. Without this, "I choose when to look" becomes "I choose which number to
  believe." The limit is per-agent, so a slow-living succulent may accept older data than a
  fern — it is its own risk to take, bounded by the cadence ceiling.
- **The cadence floor** — willful ignorance is capped by the constitutional maximum sleep.

For a *listening* agent the freshness rule changes character: it is no longer a limit on the
agent's own laziness but a **detector**. If the board goes quiet, readings age out and the
agent stops acting on them, instead of quietly using stale numbers. Same rule, and it is worth
noticing that it survives losing the cadence — because it was always about belief, not control.

# Ingest — the plant asserts its own reading

The sensing module writes each reading to Influx (history) and `:sensed` (current state)
as the **agent's own** assertion — `prov:wasGeneratedBy` the agent, no witness — per
[trusted-agent-mode](/decisions/trusted-agent-mode.md), then announces its verdict on its
event topic.

The sense mode rides along on the node, so a late board and a quiet one are distinguishable
afterwards — [observation](/domain/observation.md) says why that cannot be recovered from the
number.

Which sensors it listens to is not configured: it reads `sensing:polls` from the
[world](/decisions/world-graph.md) and subscribes exactly those topics, never a wildcard.
That is the sensor access grant made concrete — fern's agent is wired to fern's sensor and
cannot touch tomato's, because the wiring says so and the code follows it. Since each agent
is its own process, it could not reach another's sensor even if it tried.

# What a stored figure is, and when

Both questions belong to the node rather than to the sensing loop — which of the two ends the
number is, and which instant it is stamped with. [observation](/domain/observation.md) has them.

# The price of watching, and who actually spends the battery

Estimated on this bench's numbers (#151): a full radio wake — boot, WiFi, publish, release —
costs ~0.25 mAh; the ULP vigil ~150 µA, ~3.6 mAh/day. One wake buys about a hundred minutes of
watching, so the radio is the cost and the vigil is noise until heartbeats stretch past ~4
hours, where the vigil becomes the dominant term and the energy-budget seam's real question —
pricing the watching itself — begins.

The finding that outlives the numbers: **the battery is spent by the agent's epistemology, not
by the firmware.** A sentinel's heartbeat is generated under its polling agent's
`sensing:maxReadingAgeS`, so the same board is either no better than the governed node (~40
mAh/day, weeks on a cell) or four times better (~10 mAh/day, months) on nothing but that one
belief. The crossing promise is what makes a generous freshness rule safe: silence means
*nothing crossed*, freshness work moves onto the ULP, and the heartbeat only proves liveness.
A world that deploys a sentinel and keeps a twelve-minute freshness rule has bought the watcher
and declined the savings. Both firmwares are supported on equal terms — the governed node where
the agent must steer attention, the sentinel where the world's own events are the story — and
`orexis-firmware` dispatches on `mc:firmware` alone.

# Seams left open

- **Sensing is not yet priced.** The payoff of agent-owned attention is that looking costs
  energy, making observation an economic decision
  ([single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md)). v1 sets
  cadence from urgency alone; no wallet debit per `sense`. The lever exists, the price does not.
- **Cadence is a reflex, not a deliberation.** `cadence_for` is deterministic code, like the
  bid. An LLM stance could later argue for more attention; the clamp still binds.
