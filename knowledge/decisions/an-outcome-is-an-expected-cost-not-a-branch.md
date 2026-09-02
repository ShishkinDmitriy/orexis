---
type: Decision
title: An outcome is an expected cost, not a branch
status: accepted
timestamp: 2026-09-03
description: >-
  An action may state several ways of turning out, each with its effect and a likelihood;
  the search treats each as its own candidate, divides the cost by the likelihood, and a
  step relies on one. Refused: contingent plans (paying for every branch up front where
  replanning on surprise already exists); modelling the pump's chance of failing (no plan
  would branch on it); a raw win rate (a plan that flaps on one lost bid); refusing a venue
  outright at zero odds (it would never be tried again, so nothing would ever learn).
---

# An outcome is an expected cost, not a branch

The sovereign's question, 2026-09-02: a bid wins half the time, a pump raises moisture
ninety-nine times in a hundred — does the plan branch? The answer settled in discussion and
built here is that the two cases are different in kind and neither branches.

**Chance is not another agent's choice.** Losing a round is what the other bidders did: a
first-order belief about what a venue DID, which the modelling rule already allows and which
passes its one test — a belief about the odds changes which plan is selected, bid or self-dose.
A pump failing is chance, and it fails that test: no plan chosen beforehand would differ, and
the recovery is a different lever that replanning finds. So the venue's odds are believed —
two counts the bidder keeps, banded — and the pump's are telemetry.

**Replanning on surprise is the road, and it was already built.** Determinize, act, replan
(Yoon, Fern and Givan's FF-Replan) beats contingent planning on nearly every probabilistic
benchmark, because a contingent plan pays for every branch up front and most branches never
happen. Since #510 a step relies on one predicted diff, the keeper holds the world to it, and
an unmet verdict drops the tail and asks deliberation again. What this record adds is the
vocabulary for saying WHICH way a step relies on, and the one place odds enter: the action's
cost divided by the outcome's likelihood, the expected cost in attempts, ranked by the A* as
any cost is.

# What was refused

- **Contingent plans.** A then-per-verdict link in the ledger is small and the ledger already
  distinguishes met from unmet; it earns its place only where the bad branch needs
  preparation before the outcome is known — two venues at once, a butt kept in reserve
  against a deadline — and no shipped world shows that yet. The simulation's nearly-empty
  butt against a round's deadline is the likely trigger.
- **A likelihood on the pump.** Ninety-nine in a hundred would be a number nobody reads: the
  dose's plan is the same at any odds, and the one-in-a-hundred is the actuator's health,
  which sensing already reports as staleness and a dead sensor.
- **A raw win rate.** Won over entered, fresh on every round, would re-decide the plan on one
  lost bid. Banded to the quarter with an even prior, a venue's odds move only when the
  evidence does.
- **Refusing a venue at zero odds.** A venue that never allocated would be tried never again,
  and nothing would ever learn otherwise. The floor keeps it on the menu at eight times its
  price, which is what a poor venue costs.

# Seams left open

- **A market of two venues with different odds** is the world that would show the choice
  this buys; today every bidder has one venue and the odds change the plan's cost, not its
  shape.
- **Contingency links**, as above.
- **The NotAllocated outcome nets to nothing** and is discarded as a world already reached,
  which is right; a world where losing costs something — a deposit, a reputation — would give
  it an effect and a reason to be weighed.
