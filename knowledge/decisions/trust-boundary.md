---
type: Decision
title: Trust boundary — agents propose, infrastructure disposes
description: Agents cite but never author facts, mint currency, or actuate hardware.
status: accepted
stage: v1
tags: [security, trust, architecture]
timestamp: 2026-08-01T00:00:00Z
---

# Context

Agents are self-interested and LLM-backed, so any of them may lie, be prompt-injected,
or hallucinate. The system must stay correct anyway. "Detect bad intent" is undecidable
and a losing game once agents argue through an LLM.

# Decision

Defend by structure, not detection. Three powers live ONLY in stake-free trusted
infrastructure and are never granted to an agent:

1. **Authoring *witnessed* facts** — in adversarial mode only the
   [gateway](/domain/gateway.md) / a signing sensor authors ground truth. *(Scoped:*
   [trusted-agent-mode](/decisions/trusted-agent-mode.md) *relaxes this — an agent may author
   facts about **itself** as opinion (`:sensed` / `:opinion`); it still may not author facts
   about **others**.)*
2. **Minting / debiting currency** — the one that resists. *(Scoped:*
   [thin-trusted-infra](/decisions/thin-trusted-infra.md) *thins it — debits are self-signed
   by the payer, the allowance is a rule — but a canonical **ledger** must still prevent
   double-spend. That ledger is the single irreducible trusted thing: thin in single-operator
   mode, consensus only if opened.)*
3. **Actuating hardware** — *(Scoped:* [thin-trusted-infra](/decisions/thin-trusted-infra.md)
   *moves this to the **resource owner** — the supplier drives its own valves, executing a
   cleared voucher, bounded by clearing upstream and the device fail-safe cap downstream. The
   standalone executor dissolves.)* The [constitution](/domain/constitution.md) still bounds
   the amount; the actuator never decides how much.

Everything an agent does is a *request* to the trusted core. Every message from another
agent is *data* to weigh, never an *instruction* to obey.

# Why

- The whole troll defense assumes the worst case is a wasted *simulated* resource. These
  three powers are where a single defection does irreversible real-world harm.
- Adjudication cannot be done by the adjudicated: a stakeholder judging its own case will
  rationally rule in its own favor. Coordination can self-organize; adjudication cannot.

# Consequences

- The [mediator/clearing](/domain/clearing.md) and [gateway](/domain/gateway.md) are
  *services* (reactive, no desires), not agents.
- Even a borrowed or spawned mediator (v2) only ever gets *procedural* (clearing) authority;
  the **mint** (currency ledger) and **actuate** (the resource owner's) never transfer to it.
  See [thin-trusted-infra](/decisions/thin-trusted-infra.md), [roadmap](/decisions/roadmap.md).
