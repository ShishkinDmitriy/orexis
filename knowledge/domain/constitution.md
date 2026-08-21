---
type: Domain Concept
title: Constitution
description: Hard, non-negotiable constraints enforced by code, not persuasion.
---

# What it is

The "court". The separation of what's **negotiable** (politics — each agent's soft goal,
argued and traded) from what's **non-negotiable** (the constitution — hard safety/physical
constraints). No agent, vote, or clever LLM argument overrides it; it is checked
independently before any action fires.

# Constraints (examples)

- Never water a plant past its **root-rot threshold** (over-watering is negative utility).
- Total allocation ≤ **tank capacity** (conservation).
- **Budget conserved** — no minting outside the allowance.
- A plant already above target is **blocked** from receiving water.

# How it's enforced

As **SHACL shapes / rule-engine checks** over the RDF belief base — validates or doesn't,
with no argument. The first shapes exist (each package's `shapes.ttl`, run together by `agora-validate`):
every observation must be complete and world-versioned, and — under
[trusted-agent-mode](/decisions/trusted-agent-mode.md) — **self-asserted** (authored by the
plant itself; a signing sensor re-adds an independent witness in adversarial mode). The
allocation constraints are Python in `agent/clearing.py` rather than SHACL, and only one of the
two is live: **total ≤ tank fires; per-agent rot headroom cannot**, because the only production
caller passes an empty headroom map, so the branch is skipped for every line of every trade
([#270](https://github.com/ShishkinDmitriy/agora/issues/270)). Its unit test is green and
correct — it proves the check, not that anything populates it. Over-watering is still unreachable
for an honest agent, held off by deliberation declining a dose that does not improve the region
and by the device's fail-safe cap; what is inert is the layer meant to hold when those two are
the ones defecting. Whether this layer should become SHACL over the proposed trade is open. This is
why the constitution must be formal, not English: the more persuasive the agents, the more
the backstop must be immune to persuasion. See
[english-vs-formal](/decisions/english-vs-formal.md).

# Amendment

Only the sovereign (you) may amend the constitution. Agents operate within it; they cannot
change it. Amending the constitution, the topology, or charters is the same authority and
process — see [genesis](/decisions/genesis.md), which is versioned and amendable (structure
mutable, history immutable).
