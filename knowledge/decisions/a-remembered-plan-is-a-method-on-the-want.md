---
type: Decision
title: A remembered plan is a method on the want
status: accepted
timestamp: 2026-09-04
description: >-
  A plan that worked is lifted into the agent's own graph and hung on the want it served, keyed
  by the signature of the world it was decided in; the same want in the same world adopts it
  with no search, verified by the world step by step. Refused: verifying a remembered plan by
  re-simulation before adopting it (a search per reuse, where feedback already verifies);
  keying the world on everything the agent holds (the ledger and the trace change every pass);
  keeping a plan that failed (a lookup that lies is worse than a search).
---

# A remembered plan is a method on the want

The sovereign's line (2026-09-03): it does not matter who creates a method — a package, the
search, or the agent promoting a plan that worked at runtime. What makes a method a method is
that it is a stored sequence of steps hung on something the agent can choose, walked without a
search, and dropped the moment the world contradicts a step. #469 asked for the runtime half
and this builds its first honest form: a plan that reached its end is lifted FILLED into the
agent's remembered graph, hung on the want with the signature of the world it was decided in;
the next pursuit of that want in a world of that signature adopts it without a search, the
trace says `remembered`, and the keeper walks it as any plan. See
[remembered plan](/domain/remembered-plan.md).

# What was refused

- **Verification by re-simulation before adopting.** The original issue proposed forking a
  world and re-running the rules to check a remembered plan still satisfices. That is a search
  per reuse. Since #510 every step is verified by the world when it is taken, and a step whose
  prediction fails drops the tail and the search takes over — so a remembered plan is adopted
  on its signature alone and corrected by feedback, which is cheaper and no less safe.
- **Keying the world on everything.** A signature over every graph the agent holds never
  saw the same world twice: the ledger, the trace and the remembered graph itself change with
  every pass. What a plan depends on is what its rules read — the topology and the readings —
  and that alone is hashed.
- **Keeping what failed.** A remembered plan adopted again that fails a step is forgotten at
  once. A lookup that lies costs more than the search it saves.

# Seams left open

- **Lifting to variables**, the same instance across steps becoming one variable, so a plan
  applies in a world of the same shape rather than the same signature.
- **Applicability regressed through the effects, and the composed effect**, so the search can
  weigh a remembered plan as one action against the primitives and seed its bound from it.
- **Review as the forgetter**, the habit record's road: a remembered plan that stops working
  should be retired on evidence, the way a tolerance is re-picked.
