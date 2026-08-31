---
type: Decision
title: A step declares its cost, and cost breaks ties under urgency
description: >-
  #466's decision, taken with the fix. An action may carry `orexis:costs` beside
  `orexis:landsAfter` — a SELECT the owning package declares, in the wallet's unit, answered
  about whichever world is being judged — and the search ranks candidates lexicographically:
  urgency first, cost only between candidates urgency cannot separate. Refused: cost folded
  into the measure (money and wellbeing are different currencies, and mixing them is the
  strengths-of-one-scale conflation on a new axis); cost computed in the search (an invented
  number gives a convincing answer); cost outranking urgency anywhere (a society that trades
  a plant's wellbeing for money has its priorities ratified nowhere). Acquiring declares the
  first one — the bidder's own ceiling, litres times `water:maxValuePerL`, the market
  package's one deliberately domain-coupled corner speaking again — and an action that
  declares none is free, which is a statement. Metering thought stays the named follow-up.
status: accepted
timestamp: 2026-08-31T22:48:47Z
---

# A step declares its cost, and cost breaks ties under urgency

[#466](https://github.com/ShishkinDmitriy/orexis/issues/466): the planner ranked candidates by
`urgency_after` alone — strictly-less, ties to the first found — so two plans reaching the same
urgency were indistinguishable however much water, money or thought they burned. "Better plan"
had exactly one axis, while the domain already had money and
[wallet](/domain/wallet.md) reserved metering for thought.

## The shape: declared beside the effect, asked about a world

An action may carry **`orexis:costs`** exactly as it carries `orexis:landsAfter`: a SELECT the
owning package ships, substituted like an effect rule and answered about whichever world is
being judged, one binding (`?cost`), in the wallet's unit — euros, the unit of account bids
are already priced in. `effects.cost_of` runs it through the rules' own store door (public
knowledge plus this agent's records, the road #472 corrected for `landsAfter`), each search
node carries its path's cumulative cost, and **an action that declares none costs nothing —
which is a statement, not a gap**, the same reading an omitted effect or an omitted timing
gets.

The constitution's constraint holds by construction:
[control-the-derivative](/decisions/control-the-derivative-not-the-value.md) — the cost shapes
the RANKING, nothing upstream pins a price on a specific act, and the search hardcodes no
figure of its own.

## The ranking: lexicographic, urgency first

Of two candidates urgency separates, urgency decides, exactly as before. Cost speaks only
where urgency cannot: same urgency, cheaper wins. The satisficing floor is untouched — a plan
no better than standing still stays NOT_BETTER however cheap it is, because free and useless
is still useless.

## What was refused, and why

- **Cost inside the measure.** One number blending distance-from-the-aim with euros would be
  the strengths-of-one-scale conflation arriving on a new axis: wellbeing is bouletic and
  money is a budget, and a scalar that mixes them can rank but never explain. Two axes,
  compared lexicographically, keep both legible.
- **Cost computed by the search.** A planner inventing a price manufactures findings — the
  invented half-litre dose already taught that lesson once
  ([a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)). The
  declaring package owns the estimate; Acquiring's is the bidder's own ceiling
  (`$litres × water:maxValuePerL`, the pick the bidder would never exceed), honest as a bound
  where the clearing price is unknowable before the round.
- **Cost outranking urgency.** A society that trades a plant's wellbeing for money holds that
  ranking ratified nowhere. If a world ever wants frugality to beat need, that is a character
  question — the override-order seam — not a default.

# Seams left open

- **Metering thought** is the named follow-up, unchanged from
  [single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md): nothing here
  charges for a deliberation pass, so a cached plan (#469) is not yet cheaper than a fresh
  search in any number the ranking reads.
- **Only Acquiring declares a cost.** A dose spends stored litres (an opportunity cost), a
  look spends energy — both real, both unpriced, and each is one `orexis:costs` in its owning
  package's file the day a world cares.
- **The estimate is a ceiling, not the clearing price.** Under uniform price the settlement is
  usually below `maxValuePerL`; a bidder that learns its typical clearing price could declare
  a sharper estimate, and that is review's kind of move, not this record's.

# Issues this engages

Closes [#466](https://github.com/ShishkinDmitriy/orexis/issues/466); prices the reuse half of
[#469](https://github.com/ShishkinDmitriy/orexis/issues/469) once thought is metered; composes
with [#468](https://github.com/ShishkinDmitriy/orexis/issues/468)'s world-score aggregation,
which will read the same per-node figures.
