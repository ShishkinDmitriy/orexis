---
type: Decision
title: An intention stands until the world answers, and the standing rule is the whole of the patience
description: >-
  An Actuate was adopted and satisfied within milliseconds of the command, so it never stood
  and the keeper's patience absorbed nothing — the 584-dose morning — and the guard for that
  lived first in the actuator, then as an `absorbs` hook execution asked before committing.
  The BDI-shaped fix is that the intention is to the END: a self-dose stands from the command
  until its expectation is judged, exactly as an Acquire stands until its claim, `adopt`
  absorbs the next impulse by the one rule it always had, and the hook is deleted.
status: accepted
timestamp: 2026-08-25T12:00:00Z
---

# What was wrong

Two means had two lifecycles for no reason the model states. An `Acquire` stood from the first
bid to the claim, so a second impulse to buy while one stood was absorbed by `adopt` — the rule
[an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md)
gives. An `Actuate` was satisfied at the command, milliseconds after adoption, so nothing ever
stood and the same rule absorbed nothing: the gardener pulsed its pump on every second reading
all night. The fix at the time read the ledger, any outcome, for a same-means row younger than
the patience (`Keeper.within_patience`); [an-intention-is-a-plan-committed-to](/decisions/an-intention-is-a-plan-committed-to.md)
moved that guard in front of `adopt` as a hook, `absorbs(row, desire)`, because generalising it
refused a plant its next round after a claim. A hook for one actor is a special case wearing a
contract.

# What is decided

**The intention is to the end.** A self-dose's row is adopted by execution, the watch opens on
that standing row (`keeper.expect(intention, …)`, no `satisfy` first), and the keeper resolves
it **at the verdict** — satisfied whether the end was met or unmet, because the act was taken
and *satisfied-and-unmet* is the false-knowledge signature the ledger exists to record. While it
stands, `adopt` absorbs the next impulse by the standing rule. `Module.absorbs`,
`ActuationModule.absorbs` and `Keeper.within_patience` are deleted; `execution.pursue` asks
`adopt` alone.

A watch that cannot open — no baselined reading, no stated direction — resolves the row at
once, because a commitment that can never be judged must not stand for ever.

# What it changes on a dashboard

A dose in flight now counts in `intentions_standing` and can be the `oldest_intention_s`. That
is correct: it is a commitment, and a dose whose watch never closes is exactly the thing that
figure exists to show.

# Seams left open

- **A verdict on a deadline still needs a reading to arrive.** The watch is judged in
  `on_reading_recorded`, so a board that goes silent leaves the row standing until patience
  supersedes it — visible as the figure above, not closed by a clock of its own.
