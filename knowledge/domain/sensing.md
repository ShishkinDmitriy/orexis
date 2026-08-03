---
type: Domain
title: Sensing — perception as the agent's initiative
description: The agent owns when it looks (cadence), the board owns what it reads (content); ingest writes the plant's own :sensed, and a bid must cite a fresh-enough reading.
status: accepted
stage: v1
tags: [sensing, epistemics, firmware, cadence, freshness]
timestamp: 2026-08-02T00:00:00Z
---

# What it is

Perception, in **two capabilities decided by the hardware** and derived at genesis
(see [capability-modules](/decisions/capability-modules.md)):

- **`ag:Polling`** — the board is a reactive service (`sense` / `sleep`), so the
  [agent](/domain/agent.md) decides when to look and the board decides nothing.
- **`ag:Listening`** — the board is self-clocked, so it announces on its own schedule and the
  agent can only record what arrives.

Which one an agent gets is not an opinion anyone holds: it follows from `ag:senseMode` on the
device it is wired to. Reflash the board, re-run genesis, and the capability changes with it.
This is the sensing face of
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md).

# The contract

```
agent -> board   ag:commandTopic   {"sleep_s":N} (retained) | {"sense":true}   [pull only]
board -> agent   ag:readingTopic   {"value":0.183,"sensor":"..."}
agent -> peers   ag:eventTopic     {"agent":...,"value":...,"band":"LOW"}
```

Every one of those channels is **stated in the world graph** on the resource that owns it —
nothing builds a topic from a naming convention, so renaming a channel is a genesis edit. The
broker they are on is stated there too, as an `ag:MessageBus`: a channel name means nothing
without it, and members who disagree about the bus are not one society.
Both edges — an ESP32 and a virtual plant (`agora-sim`) — speak exactly this, so there is one
ingest path and nothing downstream can tell them apart.

Note what goes out on the event topic: the agent's **own verdict**, not its raw state. That is
voluntary disclosure — a host learns that scarcity has appeared without ever reading anyone's
moisture.

# Two levers, deliberately unequal

- **Cadence** (`sleep_s`) is *standing policy*, published **retained**. A board that is deep
  asleep now still receives it the instant it wakes and subscribes. This is the reliable
  lever, and the real one: to see sooner, tighten the cadence. Only a polling agent has it.
- **Sense** (`sense:true`) is a *best-effort nudge* — it lands only if the board happens to be
  awake in its listen window, and is **never retained** (a retained `sense` would re-fire on
  every wake, forever).

# Capability vs binding — what varies, and what does not

The two capabilities above say what an agent must **decide**. How a device is actually spoken
to is a separate axis, and deliberately not part of the capability: a pull-mode board on a
bus and one on a GPIO pin present the same choices and the same obligations, and differ only
in the driver that carries the message.

So the protocol lives on the **device** (`ag:onBus` plus its channels), a `Driver` is selected
per sensor from what the device declares, and the agent's attention policy is untouched by
any of it. The test for whether something belongs in a capability is whether it changes what
the agent must believe: pull-vs-push does (a cadence, or none), MQTT-vs-HTTP does not. An
agent can hold one sensor on a bus and another on a wire under a single policy — which is
exactly what naming the transport in the capability would have made impossible.

Adding a transport is therefore small: a driver, its terms, and its completeness rules. No
new capability, no belief changes.

# Cadence is desire-relative, like the band

Attention scales with how close the plant is to its own `LOW`: thirsty plants watch closely,
comfortable ones let the board sleep. The numbers are **the agent's own belief**
(`ag:fastSleepS` / `ag:slowSleepS` in `:beliefs/<agent>`), read at startup — a succulent can
reasonably watch less often than a fern, and does. The policy that turns them into a cadence
lives with the agent (`agent.cadence_for`), never on the board — same reason the band does.

Bounds (`MIN_SLEEP_S` / `MAX_SLEEP_S`) are **constitutional** and enforced in *three* places:
the SHACL shapes reject beliefs that exceed them, the agent clamps, and the firmware clamps
again on receipt. Autonomy over attention, never the freedom to sleep through a drought.

# Cadence ≠ content — why pull stays honest

Handing the agent the cadence does **not** hand it the number. It chooses *when* to look; the
sensor still authors *what* it reads. Two guards close the gap that pull opens:

- **Freshness** — a bid must cite a reading no older than the agent's own `ag:maxReadingAgeS`;
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

The perception module writes each reading to Influx (history) and `:sensed` (current state)
as the **agent's own** assertion — `prov:wasGeneratedBy` the agent, no witness — per
[trusted-agent-mode](/decisions/trusted-agent-mode.md), then announces its verdict on its
event topic.

Which sensors it listens to is not configured: it reads `ag:polls` from the
[world](/decisions/world-graph.md) and subscribes exactly those topics, never a wildcard.
That is the sensor access grant made concrete — fern's agent is wired to fern's sensor and
cannot touch tomato's, because the wiring says so and the code follows it. Since each agent
is its own process, it could not reach another's sensor even if it tried.

# Seams left open

- **Perception is not yet priced.** The payoff of agent-owned attention is that looking costs
  energy, making observation an economic decision
  ([single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md)). v1 sets
  cadence from urgency alone; no wallet debit per `sense`. The lever exists, the price does not.
- **Cadence is a reflex, not a deliberation.** `cadence_for` is deterministic code, like the
  bid. An LLM stance could later argue for more attention; the clamp still binds.
