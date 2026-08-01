---
type: Domain Concept
title: Constitution
description: Hard, non-negotiable constraints enforced by code, not persuasion.
tags: [rules, safety, shacl]
timestamp: 2026-08-01T00:00:00Z
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
with no argument. Run by the [clearing](/domain/clearing.md) step (or a rule-service it
calls), in parallel with bidding. This is why the constitution must be formal, not English:
the more persuasive the agents, the more the backstop must be immune to persuasion. See
[english-vs-formal](/decisions/english-vs-formal.md).

# Amendment

Only the sovereign (you) may amend the constitution. Agents operate within it; they cannot
change it.
