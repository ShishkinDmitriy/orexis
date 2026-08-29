---
type: Service
title: Keeper
description: >-
  The service that keeps the ledger — the only writer of the intention graph, the owner of the
  patience that absorbs a repeated impulse, and the judge of whether the world answered. It also
  holds a clock: on its own patience it hands every want to execution, which is the non-market
  entry into deliberation.
---

# What it runs

Three jobs that share one graph, and a clock.

- **Keeping.** `adopt` / `satisfy` / `drop`, each row carrying when it was adopted, how it
  resolved, and why in both directions.
- **The patience.** Within `ag:patienceS` a second impulse toward the same commitment is
  absorbed rather than re-decided — the amortisation that makes an expensive deliberator
  affordable.
- **The verification arc.** `expect` opens a watch with a baseline and a deadline; `judge` closes
  it when a number arrives; enough unmet verdicts for one pair raise a suspicion.

# What it reads and writes

![keeper — what it reads and writes](../diagrams/service-keeper.svg)

**The sole writer, and that is structural.** No other service touches the intention graph; a
one-writer scan in `tests/test_intention.py` holds it.

# What it is not

Nothing here chooses. [Execution](/domain/executor.md) hands it a plan's head; the *whether*
belongs to [deliberation](/domain/deliberator.md). And what a commitment IS — the lifecycle, the
expectation, why absorption is a cost model — is [intention](/domain/intention.md)'s to say. This
page is the service: its three jobs, its clock, and the one graph it may write.
