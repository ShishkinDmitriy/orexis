---
type: Decision
title: Trusted-agent mode — agents assert their own beliefs
description: Under a trusted-agent assumption the gateway/witness is dropped; each agent states its own current-state as opinion, and sensor access is capability-gated (genesis links agent↔sensor and grants the read).
status: accepted
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
  learning). Its interpretations. (AMENDED: it shipped as **`:classification`**. The split this
  record asks for is exactly what was built — read apart from verdict — under the name the
  modality carries.)

Both are the agent's and both are opinion, but separating them means "fern *read* 0.18" and
"fern *thinks* it's LOW" stay distinct, auditable facts — you can inspect the reading apart
from the verdict.

# Sensor access is capability-gated (isolation, not integrity)

The sensor is not wide-open. At **[genesis](/decisions/genesis.md)** the sovereign links each
agent to its sensor(s) with an **access grant** — a static capability (agent ↔ device) the
sensor checks on each read (distinct from the *claim* won per round at the auction; see
[authn-authz-capabilities](/decisions/authn-authz-capabilities.md)). This buys:

- **Isolation** — only fern's agent may read fern's sensor; no agent spies on another's
  sensor (consistent with minimal disclosure — each reads only its own).

It does **not** buy **integrity** — once fern's agent holds the reading, nothing stops it
opining a different number. In trusted mode we accept that; honesty of self-report is assumed.

The access grant is only needed for a **networked** sensor. A sensor wired directly to the
agent's own device (a Pi's GPIO) needs none — physical possession is the credential, and the
agent just reads it. Authorization tracks the connection: see *Connection determines
authorization* in [authn-authz-capabilities](/decisions/authn-authz-capabilities.md).

# What is given up, what is kept

- **Given up:** anti-fabrication of an agent's *own* state. A lying agent could misreport its
  moisture (and, if the constitution reads self-reported state, lie past a rot check). Fine
  under the trusted-agent assumption; unacceptable in an open society.
- **Kept:** the two other privileged powers (mint, actuate) stay in infra; sensor isolation
  via read-grants; the whole market layer (bids, clearing, executor) unchanged — it never
  trusted moisture anyway, only the *bid*.

# Why it's more robust than it looks — self-punishment

Because an agent reports moisture *about itself* and bears the consequences, lying is
**self-defeating in both directions**:

- **Lies wet** (reports *wetter* than reality) → bids low / cedes → stays thirsty → dries
  out. Pure self-harm.
- **Lies dry** (reports drier than reality) → bids urgently → wins water it doesn't need →
  pays for it *and* over-waters toward rot. Self-harm again.

No direction pays. Two layers enforce it: **physics** (thirst or rot) and the **economy**
(over-grabbing drains the wallet; a chronic liar goes broke and drops out — and agents can't
mint). So honesty-about-self is **incentive-compatible for a rational agent**.

# What stays open (deliberately)

- **Rival externality.** Lying *wet* is purely self-harming. Lying *dry* also grabs from a
  **shared, scarce** pool — the liar starves Tomato as well as harming itself. Self-punishment
  covers the first-order harm, not the externality (it is *bounded* by the liar's budget, not
  zero).
- **Rational vs. confused.** Self-punishment deters a *scheming* liar; it does nothing for a
  *hallucinating* one — an LLM agent that misjudges its own state and rots itself by mistake.
  In trusted mode the real risk is **incompetence, not malice**.

These two gaps are exactly why the signing-sensor seam below stays on the table rather than
being declared unnecessary.

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
