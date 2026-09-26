---
type: Capability
title: Actuation
description: >-
  The power to touch the physical world, held by whoever OWNS the hardware and by nobody else —
  a plant agent that wins water still cannot open a valve, because it owns none. Never declared:
  it falls out of holding an actuator, which is the shortest premise any capability here has.
  What it can do is bounded twice over, by a validated claim and by the device's own cap, and
  the device enforces the second itself so that a bug upstream cannot become a flood. Dosing
  figures live on the DEVICE, so recalibrating is a genesis edit rather than a code change.
---

# What it is

**Actuation is the ability to drive actuators you own.** One capability, one member today, and
the shortest premise in the project: `?agent actuation:hasActuator ?device . ?device a
sosa:Actuator`. Hold a valve, get the capability.

**No plant agent has it.** Winning water is not the same as being able to open a valve — a
[claim](/domain/claim.md) is a claim *on the owner*, redeemed by the owner — and that separation
is what keeps a market from being a way to gain physical powers you were never wired for.

# The premise is ownership, and it is deliberately not a grant

Every other [capability](/domain/capability.md) here is granted by something arguable — a region want,
a mandate, a position in a market. This one is granted by *holding the thing*, and the reason to
keep it that blunt is that actuation is the only capability whose misuse is irreversible.

A world cannot hand an agent the power to actuate without also handing it a valve, and a valve is
a physical fact somebody wired. There is no path from "the world says so" to "it can pour water"
that does not go through plumbing.

# Bounded twice, and the second bound is the device's own

What a dose may be is limited in two independent places, and the redundancy is the design:

- **by the claim** — a validated, co-signed entitlement to a quantity, single-use;
- **by `actuation:maxDoseMl`** — the device's own cap, which the firmware enforces whatever
  arrives on the wire.

The second exists precisely because the first can be wrong. A bug in matching, a replayed claim
or a mistaken decimal reaches a device that will still not pour more than its cap, so the failure
mode is a short pour rather than a flood.

`actuation:mlPerSecond` and `actuation:maxDoseMl` live **on the device**, in the world — so
recalibrating a pump is a genesis edit, and nothing about it is a code change.

# A dose is timed by the valve, not by whose pot it fills

`min(litres, the cap) / the calibration` is the open-seconds, and it is a fact about the
**valve** — a host dosing a buyer's pot needs it exactly as much as an agent dosing its own. The
first version of the rule joined through the region want instead, so every market dose fell back to a
local computation and the single source held only for self-doses, which is the half that needed it
least.

That number is the [effect](/domain/effect.md)'s `planning:landsAfter`, and the same arithmetic goes on
the wire as the command's duration. Two copies would mean planning against one timeline and
verifying against another, and the disagreement arrives looking like a device lying.

# An unconfirmed dose is not a delivered one

The valve reports that it opened; only a later [reading](/domain/reading.md) says the water
reached the pot. Those are different questions on different channels, and an agent that treats
the report as the outcome will keep dosing a pot the water never reached.

So the [intention](/domain/intention.md) that commits to a dose carries an expectation with a
baseline and a deadline, and the verdict lands beside the outcome — which is what makes
*satisfied-and-unmet* recordable rather than invisible.

# The actuation edge

> Moved here from `executor.md`, which described this as a standalone trusted party.
> [thin-trusted-infra](/decisions/thin-trusted-infra.md) had already reframed it as the
> supplier's actuation ARM rather than a component of its own, so the page was a name
> standing between two things — and the name went to the service that carries out a plan.

Like sensing, actuation splits across hardware, over the same MQTT bus — but *inverted*: the
actuation arm **publishes** a command; the pump-ESP32 **subscribes** and acts (the sensor edge is
the other way round).

```
clearing ─grant─► executor (RPi) ─publish cmd─► MQTT ─► pump-ESP32 (subscribe) ─► valve
                        ▲                                        │
                        └────────────── status/ack ─────────────┘
```

- **The actuation arm (RPi)** = decides *nothing*; validates the grant, then commands.
- **Pump-ESP32** = drives a relay/valve on GPIO. It takes commands **only** from the
  actuation arm — **never** from an agent directly. Same trust boundary as the sensor edge: the
  device is dumb and region-want-free; authority lives one hop up.

# Actuation is not sensing — the guarded subscriber

Sensing is read-only and low region wants; actuation *writes to the physical world, irreversibly*.
So the pump is a **guarded** MQTT subscriber, with four properties the sensor edge never needed:

1. **Authenticated commands** — the pump opens only on the **claim** (won this auction),
   co-signed by **host (`match_sig`) + clearing (`val_sig`)**, and verifies both — plus, for a
   networked pump, the agent's **access grant** (it's *this* agent's valve). *Access grant =
   your valve; claim = you won this dispense; neither alone opens it.* Implemented (Ed25519):
   the executor co-signs the claim; the pump rejects anything unsigned or tampered — a forged
   `actuators/fern/valve` message does nothing. The principle is **crypto proportional to
   irreversibility**: the reversible sensor path is trusted in
   [trusted-agent-mode](/decisions/trusted-agent-mode.md), but the irreversible valve is
   cryptographically gated. Keys issued once per world (`orexis-keygen <world>`), because two worlds are two societies and must not sign for each other; v1 signs both in-process. The
   token is required *because the pump is networked* — a relay on the Pi's own GPIO would need
   none (physical possession). See *Connection determines authorization* in
   [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).
2. **Idempotency** — dedup on `jti` (+ MQTT QoS 1), so a redelivered command never
   double-waters. QoS 0 could lose a command; QoS 1 + jti dedup is the right combo.
3. **Fail-safe dosing** — commands are *bounded* ("open ~N seconds ≈ N ml, then auto-close").
   The device runs a **watchdog**: it closes the valve on command expiry *and* on lost
   connection, and enforces a hard local max dose regardless of what it's told — a physical
   constitution at the edge, so a crashed executor or dropped network can't flood.
4. **Confirmation** — the pump *publishes* an ack/telemetry (`actuators/<plant>/valve/status`)
   so the executor knows water actually flowed and the receipt is truthful. Subscriber *and*
   publisher.

   **This is read now.** It was granted in PR #34 and had no listener until
   [an-unconfirmed-dose-is-not-a-delivered-one](/decisions/an-unconfirmed-dose-is-not-a-delivered-one.md),
   so a dose that never happened looked exactly like one that did. Actuation matches the report
   to the command by `jti`, and a dose nobody confirms before its deadline — that dose's own
   open-seconds plus the agent's dose grace (0.1.0's `doseGraceS`) — is logged and counted as `doses_unconfirmed`.
   **Silence is the device's refusal**, not an oversight: the valve publishes here after
   dispensing and says nothing when it rejects a command.

   An unconfirmed dose **stays spent**. The device refuses replays itself, so re-sending buys
   nothing, and a lost report followed by a re-send would risk watering twice — where an
   unopened valve costs one round the plant bids again for.

# Responsibilities (per grant)

1. **Validate the grant** — issued by clearing, what it permits matches the valve, passed the
   [constitution](/domain/constitution.md) check. In v1 the grant is a plaintext typed
   object (in-process); the JWS-signed form is a v2 transport change, not a logic change.
2. **Enforce single-use** — track `jti` (bounded, per auction) and check `auction_id`, or the same
   win settles twice (double-spend / double-actuation). This matters even without an
   adversary — a retried message shouldn't double-water.
3. **Actuate** — select the valve by the claim's **plant ID** (the supplier's genesis-
   configured `{plant_id → valve}` map — see [supplier](/domain/supplier.md)); open it for the
   claim's litres, then stop. Sequence multiple claims safely (one source, many plants).
4. **Confirm** — report completion so the auction can close and the receipt is truthful.

# What it must never do

- Take a command from an agent. Agents receive a *receipt* (proof of allocation), never a
  valve-trigger they redeem. The actuation grant flows clearing → executor **internally**.
- Re-decide the allocation. It applies a committed grant; it does not judge bids.
- Mint or attest. Those powers stay in [clearing](/domain/clearing.md) and the
  [gateway](/domain/gateway.md) respectively. See [trust-boundary](/decisions/trust-boundary.md).

# Invariant

Deterministic and injection-proof: the grant is data with a checkable shape, agent messages
are never instructions. Fully unit-testable in isolation — scripted grants in, asserted
valve action out, no model and no hardware in the loop (mock the pump-ESP32). The single
source of physical action.

# Device identity (v1 vs v2)

v1: trusted LAN + device id. v2: the pump-ESP32 gets a device cert and the executor's
command is a signed, sender-constrained instruction — same cert model as the sensor edge and
the agents. See [gateway](/domain/gateway.md) and
[authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# Related

- [claim](/domain/claim.md) — the entitlement a dose is opened against.
- [step](/domain/step.md) — a valve is what `actuation:valve` is bound to on a row.
