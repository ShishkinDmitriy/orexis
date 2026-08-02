---
type: Component
title: Executor
description: The trusted actuator — validates the capability grant and drives the pump/valve; the only thing that touches hardware.
tags: [infrastructure, trusted, actuation, capabilities, esp32]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

> **Reframed ([thin-trusted-infra](/decisions/thin-trusted-infra.md)):** actuation is *not*
> separate stake-free infra — the **resource owner (the [supplier](/domain/supplier.md))**
> drives its own valves. The "executor" is the supplier's **actuation arm**, not a distinct
> component. It *executes* a voucher (how much) + topology (which valve); it does not decide.
> Safe not because the actuator is neutral, but because the amount is bounded *above* by
> clearing (a valid, cleared voucher it can't forge) and *below* by the device fail-safe cap.
> The description below still holds as the **resource server** role — it's just hosted by the
> supplier now, not a standalone trusted party.

Consumes a validated **voucher** and performs the water leg of the trade — the one act that is
physically irreversible (you can't un-flood a root-rotted plant). It **decides nothing**:
reactive, no desires, no LLM. See [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# The actuation edge

Like sensing, actuation splits across hardware, over the same MQTT bus — but *inverted*: the
executor **publishes** a command; the pump-ESP32 **subscribes** and acts (the sensor edge is
the other way round).

```
clearing ─grant─► executor (RPi) ─publish cmd─► MQTT ─► pump-ESP32 (subscribe) ─► valve
                        ▲                                        │
                        └────────────── status/ack ─────────────┘
```

- **Executor (RPi)** = decides *nothing*; validates the grant, then commands.
- **Pump-ESP32** = drives a relay/valve on GPIO. It takes commands **only** from the
  executor — **never** from an agent directly. Same trust boundary as the sensor edge: the
  device is dumb and stake-free; authority lives one hop up.

# Actuation is not sensing — the guarded subscriber

Sensing is read-only and low-stakes; actuation *writes to the physical world, irreversibly*.
So the pump is a **guarded** MQTT subscriber, with four properties the sensor edge never needed:

1. **Authenticated commands** — the pump opens only on the **voucher** (won this round),
   co-signed by **host (`match_sig`) + clearing (`val_sig`)**, and verifies both — plus, for a
   networked pump, the agent's **access grant** (it's *this* agent's valve). *Access grant =
   your valve; voucher = you won this dispense; neither alone opens it.* Implemented (Ed25519):
   the executor co-signs the voucher; the pump rejects anything unsigned or tampered — a forged
   `actuators/fern/valve` message does nothing. The principle is **crypto proportional to
   irreversibility**: the reversible sensor path is trusted in
   [trusted-agent-mode](/decisions/trusted-agent-mode.md), but the irreversible valve is
   cryptographically gated. Keys issued once (`agora-keygen`); v1 signs both in-process. The
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

# Responsibilities (per grant)

1. **Validate the grant** — issued by clearing, scope matches the valve, passed the
   [constitution](/domain/constitution.md) check. In v1 the grant is a plaintext typed
   object (in-process); the JWS-signed form is a v2 transport change, not a logic change.
2. **Enforce single-use** — track `jti` (bounded, per round) and check `round`, or the same
   win settles twice (double-spend / double-actuation). This matters even without an
   adversary — a retried message shouldn't double-water.
3. **Actuate** — select the valve by the voucher's **plant ID** (the supplier's genesis-
   configured `{plant_id → valve}` map — see [supplier](/domain/supplier.md)); open it for the
   voucher's litres, then stop. Sequence multiple vouchers safely (one source, many plants).
4. **Confirm** — report completion so the round can close and the receipt is truthful.

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
