---
type: Decision
title: A method is the steps an action comes to
status: accepted
timestamp: 2026-09-03
description: >-
  An action the search chooses may be abstract, and the package that owns it declares the
  steps taking it comes to; the keeper expands them at adoption and walks them on feedback,
  each step declaring what it waits for. Refused: expanding methods inside the search (the
  protocol is not a choice); one search per protocol move (a bid answered by the market's
  knock needs no second decision); the reaction chain in the bidder's Python (a claim held in
  a dict is a wait the ledger cannot see).
---

# A method is the steps an action comes to

The sovereign's direction (2026-09-02): the market protocol should be a plan a package
prepares, and the courier-and-hanoi world should be planning inside another — HTN's shape.
Built here for the market: Acquiring stays the searched action, and the package declares
`orexis:method ( market:Tendering market:Presenting )`. The keeper expands a step of Acquiring
into those two at adoption, the last inheriting the reading Acquiring predicted, and steps
through them as it steps through any plan (#510). Each step's action declares what it waits
for — `orexis:readyWhen`, `orexis:doneWhen`, `orexis:lapsesAt` — as SELECT templates bound with
the rules' own tokens, and the keeper holds the step on them through the primitive it already
had (#512, #514). The claim a round clears to the bidder is a fact in its own graph, which is
what a step can wait on. See [method](/domain/method.md).

# What was refused

- **Expanding methods inside the search.** The search could have simulated tender and present
  as steps. Their effects are nothing the want reads — a bid row, a redeem message — and the
  protocol is not a choice: once Acquiring is chosen, the moves are fixed. Simulating them
  would spend the budget on worlds that differ in nothing the measure sees.
- **One search per protocol move.** The old road re-decided at every knock: an offer woke the
  deliberator, a claim adopted Presenting on its own. A bid adopted on the keeper's tick is
  answered by the market's knock without a second search, which the amortisation always
  promised; the method makes it literal.
- **The reaction chain.** `on_claim` held the claim in a dict, adopted Presenting held on a
  shape it built by hand, and `on_offer` dropped a standing Acquiring when the previous round
  closed. Each was a wait or a verdict the ledger could not show. Now a claim is a triple,
  Presenting's readiness is the action's declaration, and a lost round is the tender lapsing
  at the close — the ledger says it, and the sovereign can ask.

# Seams left open

- **One level.** A method naming an action with a method of its own is expanded one level;
  nesting waits for the courier-and-hanoi world, where a Move comes to drives.
- **The residual rides on the method's last step.** The market's review rule reads residuals
  off Acquiring, Tendering and Presenting alike, since the prediction moved to the step that
  carries it.
- **A world watch and a step wait are one primitive.** Both are `orexis:answeredWhen` holds;
  the keeper tells them apart by the baseline, and the reports count only the world's.
