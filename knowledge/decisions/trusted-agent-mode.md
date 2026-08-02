---
type: Decision
title: Trusted-agent mode — agents assert their own beliefs
description: Under a trusted-agent assumption the gateway/witness is dropped; each agent states its own current-state as opinion, and sensor access is capability-gated (genesis links agent↔sensor and grants the read).
status: accepted
stage: v1
tags: [trust, gateway, capabilities, genesis, mode]
timestamp: 2026-08-02T00:00:00Z
---

# Context

The [gateway](/domain/gateway.md) exists for one irreducible reason: a self-interested agent
must not author its own measurement (a thirsty plant would report bone-dry). That threat is
real only in an **adversarial** society. For a **single-operator, non-adversarial**
deployment (you run all the agents; they may err but won't maliciously lie to flood
themselves), the witness is defending against a threat that isn't there.

# Decision — a scoped "trusted-agent mode"

Under an explicit **trusted-agent assumption**, drop the gateway/witness and let each agent
**state its own current-state as its own opinion** — self-asserted belief, not witnessed
truth. This deliberately relaxes [trust-boundary](/decisions/trust-boundary.md)'s first
power ("agents cite but never author facts"): an agent may now author facts **about itself**.
It still may **not** author facts about *others*, mint currency, or actuate hardware — those
stay in trusted infrastructure.

So `:attested` (witnessed) becomes **asserted** — self-authored, `prov:wasGeneratedBy` the
plant itself, understood as opinion. And it splits into **two named graphs per kind**, which
keeps the measurement-vs-judgment line even without a witness:

- **`:sensed`** — the agent's **sensor data**: what it read (`hasSimpleResult 0.18`). Its
  record of observations.
- **`:opinion`** — the agent's **judgments**: what it concludes (band `LOW`, valuation,
  learning). Its interpretations.

Both are the agent's and both are opinion, but separating them means "fern *read* 0.18" and
"fern *thinks* it's LOW" stay distinct, auditable facts — you can inspect the reading apart
from the verdict.

# Sensor access is capability-gated (isolation, not integrity)

The sensor is not wide-open. At **[genesis](/decisions/genesis.md)** the sovereign links each
agent to its sensor(s) and issues a **read-grant** — a capability the sensor checks on every
read (the same [capability model](/decisions/authn-authz-capabilities.md) as settlement,
applied to reads). This buys:

- **Isolation** — only fern's agent may read fern's sensor; no agent spies on another's
  sensor (consistent with minimal disclosure — each reads only its own).

It does **not** buy **integrity** — once fern's agent holds the reading, nothing stops it
opining a different number. In trusted mode we accept that; honesty of self-report is assumed.

# What is given up, what is kept

- **Given up:** anti-fabrication of an agent's *own* state. A lying agent could misreport its
  moisture (and, if the constitution reads self-reported state, lie past a rot check). Fine
  under the trusted-agent assumption; unacceptable in an open society.
- **Kept:** the two other privileged powers (mint, actuate) stay in infra; sensor isolation
  via read-grants; the whole market layer (bids, clearing, executor) unchanged — it never
  trusted moisture anyway, only the *bid*.

# The seam back to adversarial mode

Restoring anti-fabrication does **not** require the gateway process back. Move the witness
onto the **sensor**: a signing sensor (device cert) authors its own readings, so the *stake-
free device* attests, not the *staked agent*. Then `prov:wasGeneratedBy` is the sensor's key
and readings are verifiable again — adversarial-safe, still no central gateway. Keep this
seam open; do not assume trusted-mode everywhere.

# Consequences

- The **gateway process is decommissioned**; its store-writing (bridge) folds into the sensor
  edge — in simulation the virtual plant writes its own belief; on real hardware the device
  writes (presenting its read-grant).
- **Provenance** on current-state flips from `:gateway` to the plant; the "leash as a SHACL
  shape" relaxes from *authored-by-gateway* to *self-asserted*.
- v1 runs trusted-mode (personal deployment). The signing-sensor seam is the path to an open
  society. See [roadmap](/decisions/roadmap.md).
