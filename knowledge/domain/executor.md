---
type: Component
title: Executor
description: The trusted actuator — validates the capability grant and drives the pump/valve; the only thing that touches hardware.
tags: [infrastructure, trusted, actuation, capabilities, esp32]
timestamp: 2026-08-01T00:00:00Z
---

# What it is

Trusted, stake-free infrastructure that holds the **actuate** power — the one power where a
single bad act is physically irreversible (you can't un-flood a root-rotted plant). It is
**not an agent**: reactive, no desires, no LLM. In the AuthN/AuthZ model it is the
**resource server** — it consumes the capability grant that [clearing](/domain/clearing.md)
issues and performs the water leg of the trade. See
[authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# The actuation edge

Like sensing, actuation splits across hardware:

```
clearing ──grant──► executor (RPi) ──validated command──► pump-ESP32 ──► valve
```

- **Executor (RPi)** = decides *nothing*; validates the grant, then commands.
- **Pump-ESP32** = drives a relay/valve on GPIO. It takes commands **only** from the
  executor — **never** from an agent directly. Same trust boundary as the sensor edge: the
  device is dumb and stake-free; authority lives one hop up.

# Responsibilities (per grant)

1. **Validate the grant** — issued by clearing, scope matches the valve, passed the
   [constitution](/domain/constitution.md) check. In v1 the grant is a plaintext typed
   object (in-process); the JWS-signed form is a v2 transport change, not a logic change.
2. **Enforce single-use** — track `jti` (bounded, per round) and check `round`, or the same
   win settles twice (double-spend / double-actuation). This matters even without an
   adversary — a retried message shouldn't double-water.
3. **Actuate** — command the pump-ESP32 to open the valve for the granted litres, then stop.
   Sequence multiple grants safely (one pump, many plants).
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
