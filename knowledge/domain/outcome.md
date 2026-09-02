---
type: Domain Concept
title: Outcome
term: http://example.org/orexis#Outcome
description: >-
  One of the ways taking an action may turn out — its own effect and its likelihood. An
  action stating none has one, itself. The search treats each as its own candidate, divides
  the action's cost by the likelihood, and a step relies on the one it was planned through;
  the world is held to that one. Never a branch in the plan.
---

# What it is

`orexis:Outcome`. An [action](/domain/action.md) that may turn out more than one way states
its [effect](/domain/effect.md) on each way rather than on itself: each outcome carries its
own `sh:construct`, `orexis:retracts` and `orexis:landsAfter`, and an `orexis:likelihood` —
a SELECT answering the probability that taking the action turns out this way, asked with the
rule's own tokens. An action stating no outcome has exactly one, itself, and nothing changes
for it: the dose, the move, the drive.

The market's Acquiring is the one that ships with two. `market:Allocated` is the round
clearing to me, with the effect the rule always predicted; `market:NotAllocated` is the round
clearing to someone else or nobody, with an effect that constructs nothing. Its likelihood
is read off two counts the bidder keeps on the venue in its own graph — rounds entered,
rounds won — banded to the quarter with an even prior, floored so a venue that never
allocates is still tried at eight times its price rather than refused.

# How the search uses it

**As expected cost, never as a branch.** Every way of turning out is its own candidate
(all-outcomes determinization). The action's `orexis:costs` is divided by the outcome's
likelihood: a bid at half odds costs twice its price, because that is what it costs in
attempts on average. That is the whole of how odds choose between a venue and a butt, or
between two venues — through the cost the A* already ranks by — and the plan that comes out
is still a sequence. A [step](/domain/step.md) records the outcome it was planned through as
`orexis:reliesOn`; its `orexis:predicts` is that outcome's diff, and the keeper holds the
world to it. The other way turning out is an unmet verdict, the tail is dropped, and
deliberation decides again from the world as it is: determinize, act, replan on surprise.

# What it is not

**Not chance.** Losing a round is what the other bidders did — a first-order fact about
the venue, which is why it may be believed and why a plan may branch on it. A pump that fails
one time in a hundred is chance, and no plan chosen beforehand would differ, so it is not
modelled at all; the recovery is a different lever that replanning finds. The rule that
splits them is the modelling rule: believe it only if a plan would branch on it.

**Not a contingent plan.** A plan that carried both branches would pay for every branch up
front, and most never happen. Where the bad branch needs preparation before the outcome is
known — two venues at once, a butt kept in reserve against a deadline — a then-per-verdict
link in the ledger would be the shape, and it waits for a world that shows the need.

**Not a raw rate.** The likelihood is banded, because a plan re-decided on every round's
fresh fraction would flap between a venue and a butt on one lost bid.

See [an-outcome-is-an-expected-cost-not-a-branch](/decisions/an-outcome-is-an-expected-cost-not-a-branch.md).
