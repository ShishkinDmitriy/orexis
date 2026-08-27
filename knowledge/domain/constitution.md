---
type: Domain Concept
title: Constitution
description: Hard, non-negotiable constraints enforced by code, not persuasion.
---

# What it is

The "court". The separation of what's **negotiable** (politics — each agent's soft desire,
argued and traded) from what's **non-negotiable** (the constitution — hard safety/physical
constraints). No agent, vote, or clever LLM argument overrides it; it is checked
independently before any action fires.

# Constraints (examples)

- Never allocate a participant more than its subject could survive being moved by — the
  **allocation ceiling**, which for a plant is the root-rot end of its survival range.
- Total allocation ≤ **tank capacity** (conservation).
- **Budget conserved** — no minting outside the allowance.
- A plant already above target is **blocked** from receiving water.

# How it's enforced

As **SHACL shapes / rule-engine checks** over the RDF belief base — validates or doesn't,
with no argument. The first shapes exist (each package's `shapes.ttl`, run together by `orexis-validate`):
every observation must be complete and world-versioned, and — under
[trusted-agent-mode](/decisions/trusted-agent-mode.md) — **self-asserted** (authored by the
plant itself; a signing sensor re-adds an independent witness in adversarial mode). The
allocation constraints are Python in `packages/orexis-capability-market/clearing.py` rather than SHACL, and **both are now
live**: total ≤ tank, and a per-participant **allocation ceiling** ([#270](https://github.com/ShishkinDmitriy/orexis/issues/270)).

The ceiling is **structural, and that is what makes it safe to compute**. It is the span of what
the participant's subject survives, in litres — bone dry to the wet cliff — derived at genesis
from facts a host is allowed to hold. It is deliberately NOT a live headroom measured from where
the subject is now: a host cannot see a bidder's state and must not need to
([agent-centric-epistemics](/decisions/agent-centric-epistemics.md)). No honest allocation ever
needs more than the span, because the span is the whole distance the subject could legitimately
be moved, so a line asking for more can only overshoot whichever end it started from. Bound the
envelope, never the dose.

The domain computes it and the kernel reads it, on the `market:lotCapacity` precedent: what
counts as too much water is a fact about plants, and `packages/orexis-capability-market/clearing.py` must name no domain.
**Absent is not zero** — a participant whose subject states no survival range has no ceiling and
is not checked, because nothing in the world says what too much would be for it.

Whether this layer should become SHACL over the proposed trade, and whether a host should CLAMP a
greedy bid rather than let clearing refuse the whole trade, are both open. This is
why the constitution must be formal, not English: the more persuasive the agents, the more
the backstop must be immune to persuasion. See
[english-vs-formal](/decisions/english-vs-formal.md).

# Amendment

Only the sovereign (you) may amend the constitution. Agents operate within it; they cannot
change it. Amending the constitution, the topology, or charters is the same authority and
process — see [genesis](/decisions/genesis.md), which is versioned and amendable (structure
mutable, history immutable).
