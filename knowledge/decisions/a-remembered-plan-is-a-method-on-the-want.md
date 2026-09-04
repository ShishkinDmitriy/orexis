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
  keeping a plan that failed (a lookup that lies is worse than a search). Amended 2026-09-04:
  in a world of another signature the remembered plan is weighed as one candidate on the
  menu, walked step by step in the imaginarium and settled like any step, its cost seeding
  the bound; refused there was adopting it unverified where the world differs.
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

# Amended 2026-09-04: weighed as one candidate where the world differs

The sovereign's question that reopened this: when we plan, does it matter whether a thing is
an action or a method? It should not — and under the first form it did, three ways: an action
was searched, a declared method was walked at adoption, and a remembered plan short-circuited
the search or was ignored. The second form closes the composed-effect seam by putting the
remembered plan ON THE MENU. In a world whose signature is not the one it was lifted in, every
plan remembered for the want is a candidate at the root, weighed before any primitive: its
steps are re-simulated in order, each taken only where the menu of the world the previous step
reached offers that very row — the same action through the same lever about the same thing —
and the world the walk reaches is settled exactly as a primitive's world is: forbidden, dear,
late, seen or met. Its composed effect is the world reached; its applicability is that every
step was on its menu; where it still achieves the want, its cost is the bound the rest of the
pass is refused by, and among achievers tying on cost the route already walked wins. The trace
names it as what would be taken and, when chosen, as what was chosen — as the route, not as the
first of its steps. A step off the menu is the plan not applying here, said as a verdict rather
than guessed around. A route that fails when walked is forgotten by its steps, whichever road
adopted it, and a route the search finds again is not remembered twice.

**What stands from the first form, and why.** The exact hit — the same want in a world of the
same signature — is still adopted with no search. The refusal above argued that re-simulating
before adopting is a search per reuse; it is, in that world, because the pass that lifted the
plan searched that very world and would find the same answer. Where the world differs the
argument does not reach, and there the plan was not used at all; walking it costs one fork per
step, which is not a search, and the budget bounds what is looked at after.

**Refused here:** adopting a remembered plan unverified in a world of a different signature.
Feedback would correct it step by step, but a step that fails is a patience spent, and the
imaginarium can say for a fork per step what the world would say for a patience per step.

# Seams left open

- **Lifting to variables**, the same instance across steps becoming one variable, so a plan
  applies in a world of the same shape rather than the same signature.
- **Applicability regressed through the effects**, so a plan that cannot apply is seen to be
  inapplicable without being walked — today a step off the menu costs the forks before it.
- **Review as the forgetter**, the habit record's road: a remembered plan that stops working
  should be retired on evidence, the way a tolerance is re-picked.
