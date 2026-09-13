---
type: Decision
title: One expectation, and the reading is held to it
status: accepted
timestamp: 2026-09-13T17:00:00Z
description: >-
  The sovereign's grooming of 2026-09-13, after the expected next observation landed beside
  the keeper's watch and the two were seen to be one thing computed three ways. ONE
  expectation per subject and property, the next observation in a window and in a set of
  bands from the branch the agent is on — the drift's, or a standing step's from its landing;
  ONE comparison when the reading arrives, in sensing, and its outcome is everyone's verdict:
  a standing step is met or unmet, the mind is woken on a surprise and on a missed window and
  on nothing else, and the cone already identifies the present by the same look. Retired — the
  answering shape built per step and its compiled hold, the watch on a number, the reviser
  waking on every reading, and hysteresis in time (#615), whose work the stated width does.
---

# The claim

**An expectation is one kind of fact.** For every subject and property this agent senses there
is one expected next observation
([prediction](/domain/prediction.md)): the window the next reading is due in, and the set of
bands it may be. The set is read off the branch the agent is on. With nothing standing it is
the world's own branch — the reading in hand carried by the [drift](/domain/effect.md) to the
window's far end, widened by the instrument's noise and by what the drift states beside its
rate. With a [step](/domain/step.md) standing whose landing falls inside the window, it is
the intended branch: from the landing on, the band the step's effect declared, carried by the
drift after it. That is what
[a-prediction-is-a-set-of-bands-that-widens-with-the-horizon](/decisions/a-prediction-is-a-set-of-bands-that-widens-with-the-horizon.md)
said in one sentence and left unbuilt: the sequence is the do-nothing branch until an
intention stands and the intended branch after, and the keeper's expectation on a step's end
and the expected next observation are then one fact.

**The reading is compared with it once, and the outcome is everyone's verdict.** When a reading
arrives, sensing — which owns readings and what band they are — looks once at whether it is
in the set. Three outcomes, and nothing else:

- **Absorbed.** The reading is in the set: the world is going on as believed. No pass. A
  standing step whose landing has come and whose band the reading is in is MET, and its plan
  advances.
- **Surprise.** The reading is outside the set: a pass is woken that names the surprise. A
  standing step past its landing whose band the reading is not in is UNMET: the tail is
  dropped and the failure is told upward, as today.
- **Missed.** The window closes with no reading: the reading in hand is stale, the freshness
  want wakes, the expectation is gone. Staleness said once, and the only clock in the
  mechanism is the timer that lands this.

A step's own deadline stays the keeper's: a window that closes without the step's band ever
arriving is unmet at the deadline, on the scheduler, exactly as now.

**The cone already identifies the present by this look.** The planner matches the present to a
kept world by what a reading IS within the want's view — the band the domain asserted on it
(#576) — and the keeper's verdict and the reviser's surprise are that same test asked of the
reading that arrived. One look, three readers, and none of them a shape.

# What it retires

- **The answering shape built per step, and its compiled hold.** `expect` generated a SHACL
  shape of the observation that would answer, asked of sensing through `orexis:answer`,
  compiled it to a select and held the step on it as `answeredWhen`, re-asked on every write.
  It was correct and it was a second rendering of the expectation, and a rendering with a
  blind spot the suite found the day the two stood side by side: a node that states no value
  passes a constraint on a value vacuously, so the expectation itself read as the answer. The
  step's prediction goes INTO the expectation instead, and the comparison at arrival is the
  verdict. A plain fact a step predicts — a claim held, a round opened — is not an
  observation and keeps its hold: present for an addition, gone for a retraction, as one
  query under a shape, which is `doneWhen`'s road.
- **The watch on a number.** A caller could hand in a number and the world was held to it
  exactly; a value is a band collapsed, and what the search plans on is the band an effect
  declares (#579). A number stated by hand is held to the band it falls in, and the number
  itself lives where it always did, in the residual the reviewer reads.
- **The reviser waking on every reading.** The seam's own docstring named this as its next
  job — bands, not raw values — and the storm
  ([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md))
  was its cost. A reading inside the set is not worth a pass; one outside is, and says why.
- **Hysteresis in time** ([#615](https://github.com/ShishkinDmitriy/orexis/issues/615)).
  A dwell was proposed so a reading flickering at a boundary would not wake the mind per
  crossing. The stated width does that work and invents nothing: a reading at 11.98 against
  a region starting at 12, with the instrument's noise stated, is expected in BOTH bands, so
  the flip is inside the set and absorbed. A world stating no noise still flips, and then the
  flip IS a surprise, honestly. Refused, and the issue closes on this record.

# What stays, and why

- **The residual.** The number an actor aimed at beside the number the world showed, written
  on the step at the verdict; the review rules that re-pick a conversion or widen a tolerance
  read it and nothing here changes their evidence.
- **Suspicion.** A run of unmet verdicts marks an affordance suspect and one success resets it;
  the verdict is the same fact, arriving by one road instead of two.
- **The remembered plan.** A plan that reached its end is lifted as a method on the want.
- **The crossing.** `orexis:crossesAfter` stays the drift's analytic answer to WHEN the region
  is left; the safe direction ([#633](https://github.com/ShishkinDmitriy/orexis/issues/633))
  is the same widening applied to it.
- **Plain-fact holds, readiness holds, `doneWhen`, `lapsesAt`.** Waits on the world that are
  not waits for a reading are untouched.

# The word

"Expectation" names one thing from here on: the expected next observation, sensing's. What
the keeper keeps on a step is its **stake** in that expectation — the band it promised from
its landing — and the row that says so is a *watch*, which is the word the bundle already
uses for it. `OpenExpectation` and `open_expectations` are the old rendering's names and go
with it.

# What is built, in the order it is built

1. **The keeper hands its prediction to the expectation, and the verdict comes from the
   comparison** ([#639](https://github.com/ShishkinDmitriy/orexis/issues/639)): a kernel
   extension point, `orexis:predicted`, told when a watch opens and when it closes; sensing
   folds every standing step's band into the expectation from its landing; at arrival it
   compares once and says to the keeper which watches the reading met and which it failed;
   the answering shape, `orexis:answer`, the compiled `answeredWhen` hold for observations
   and the watch on a number are retired. Held to the old answers by the suite.
2. **The reviser wakes on a surprise and on a missed window, and on nothing else**
   ([#632](https://github.com/ShishkinDmitriy/orexis/issues/632)); #615 closes on this record.
3. **The crossing is the first instant the set may leave the region**
   ([#633](https://github.com/ShishkinDmitriy/orexis/issues/633)).
4. **The word** ([#640](https://github.com/ShishkinDmitriy/orexis/issues/640)): the keeper's
   row is a watch in every identifier, and the bundle says which is which.

# Seams left open

- **A step about a subject this agent does not sense.** Nobody can witness it; the keeper
  refuses to open the watch, as it does today, and the plan runs on the deadline alone.
- **Two steps landing inside one window.** The intended branch is the LAST step's band from
  its landing; a plan whose steps land closer together than the cadence is judged by its
  last step, which is the only one a reading can tell apart.
- **Resuming from the branch point** ([#527](https://github.com/ShishkinDmitriy/orexis/issues/527)):
  a surprise now names the step and the band it failed, which is what a resumed frontier
  would need; whether keeping it pays is still the measurement that issue asks for.
- **A reading between the taking and the landing.** It is compared with the drift's branch
  and says nothing about the step; a world that answers early is absorbed and the step is met
  by the first reading after its landing.
