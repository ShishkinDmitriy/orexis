---
type: Decision
title: The search reads predictions and computes none
status: accepted
timestamp: 2026-09-13T18:00:00Z
description: >-
  The sovereign's grooming of 2026-09-13, after the expected next observation landed beside
  the drift and the keeper's watch: "replace the drift with a bunch of predictions — how they
  were calculated is the package's decision; that a prediction exists is what affects
  planning." A PREDICTION is a graph holding during a period whose keyed facts stand in for
  the present's while it holds, written by whichever package predicts, at the horizons it
  chooses, in the words the present is written in. The search reads the prediction holding at
  a node's instant and computes no physics at any fork; the crossing is the first prediction
  at which the root reads unmet; the expected next observation is the first prediction; and
  one comparison at arrival is every verdict. Retired — the drift run inside the search, the
  projected root, the crossing and spread rules as kernel words, the set-of-bands predicate,
  the answering shape built per step, the watch on a number, the reviser waking on every
  reading, and hysteresis in time (#615).
---

# The claim

**A prediction is a graph holding during a period, and its facts stand in for the present's.**
[a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md) gave every
graph a period and the door hands a reader what holds at the instant asked about; a
forecast of the outside already arrives that way. A prediction is that, said of the agent's
own subject: a graph, `orexis:PredictionGraph`, holding during the window it predicts for,
carrying what the package expects — a predicted reading keyed exactly as the present's reading
is, typed with EVERY band it may be in at that horizon, a centre value where the package has
one — in the same words the present is written in. A rule reading readings reads a predicted
world as it reads the present. The kind is the door's to know: `query_at` hands the
predictions holding at an instant beside the public knowledge and the records holding then,
no validation reads them, and the agent's own records never list them.

**Packages write them, and how is theirs.** What the drift was — a rule the kernel ran at every
fork, over `$elapsed`, with a rate the world states — becomes a text the package declares
(`orexis:predicts`) and the kernel's PREDICTOR runs at the horizons the package lists beside
it, after every reading, writing one graph per horizon with its period. Sensing contributes
the first horizon, the next reading's window, which is where its expected next observation
goes. The water package predicts from its rate, the market's host from its ledger of
arrivals, the climate from its diffusion, a forecast service from nothing of ours; the width
— the instrument's noise, the rate's give-or-take — is folded by the package into the bands it
types the prediction with, and no kernel word names it. This is the ruling of
[a-prediction-is-a-set-of-bands-that-widens-with-the-horizon](/decisions/a-prediction-is-a-set-of-bands-that-widens-with-the-horizon.md)
given its home: the sequence of bands widening with the horizon IS the sequence of prediction
graphs, and what the search reads is the bands.

**The search reads them and computes none.** A node's world is the present with the path's
diffs applied and, for every keyed fact a prediction holding at the node's instant carries,
the predicted fact in place of the present's — except a key the path itself changed, because
the plan's branch beats the do-nothing branch. The overlay fills the slot the drift filled at
each fork, so the node's signature, the ground and the cone are untouched. A pass for a want
met at an instant stands at that instant and reads what is predicted then; there is no
projected root and no drift by lead and age, and the trap #619 opened — a drift counted from
the wrong clock — has nothing to count.

**The crossing is generic.** An `orexis:At` want is derived at the start of the earliest
prediction at which the root reads UNMET, the root's own met-test asked through the door at
each prediction's start. A prediction typed with the region band and the one below reads
unmet, so the safe direction ([#633](https://github.com/ShishkinDmitriy/orexis/issues/633))
falls out of the bands and no kernel line knows a rate.

**The expected next observation is the first prediction, and the reading is held to it once.**
When a reading arrives, sensing — which owns readings and what band they are — looks once at
whether it is in the bands the first prediction typed, and that one look is every verdict:

- **Absorbed.** In the bands: the world goes on as believed, no pass. A standing step whose
  landing has come and whose band the reading is in is MET, and its plan advances.
- **Surprise.** Outside them: a pass is woken that names the surprise. A standing step past
  its landing whose band the reading is not in is UNMET; the tail is dropped and the failure
  is told upward, as today.
- **Missed.** The window closes with no reading: the reading in hand is stale, the freshness
  want wakes, and the next prediction is what the next reading is held to.

A standing step enters the predictions through the keeper: when a watch opens it tells the
kernel point `orexis:predicted` — the step, the band it declared, the instant it lands — and
the predictor rewrites the package's predictions from the landing on, starting from that
band; when the watch closes it tells the point again and the do-nothing branch returns. The
intended branch is then a prediction like any other, read by the search, the reviser and the
sovereign alike. The cone already identifies the present by the same look, a reading by what
it IS within the want's view (#576): one test, three readers, and none of them a shape.

# What it retires

- **The drift run inside the search.** `_drifted` at every fork, `_projected` at the root,
  `effects.drift`, `drifts_of`, `crossings`, `spreads`, the `$elapsed` token, and
  `orexis:Drift` with `sh:construct`, `orexis:retracts`, `orexis:crossesAfter` and
  `orexis:spreadsBy` as kernel words. A package's construct survives as its `orexis:predicts`
  text, run by the predictor and never inside a pass. The two-cones record's own seam —
  "a drift cannot drift the present's reading over its own age" — closes because nothing
  drifts: a prediction is at an instant, and the present is the present.
- **The set-of-bands predicate.** `sensing:mayBe`, `sensing:ExpectedObservation` and
  `sensing:ExpectationsGraph` (#631) were the first prediction under other words. In a
  predicted world a reading IS every band it may be in — `rdf:type`, as the present's reading
  carries its band — and a shape that refuses one of them refuses the world, which is the
  safe direction said once. A kernel reading a set-of-possibility predicate would be a
  sensing word in the kernel; the types are the words every rule already reads.
- **The answering shape built per step, and its compiled hold.** `expect` generated a SHACL
  shape of the observation that would answer, asked of sensing through `orexis:answer`,
  compiled it and held the step on it as `answeredWhen`, re-asked on every write. It was a
  second rendering of the prediction, with a blind spot the suite found the day the two stood
  side by side: a node that states no value passes a constraint on a value vacuously. The
  step's band goes INTO the predictions instead, and the comparison at arrival is the verdict.
  A plain fact a step predicts — a claim held, a round opened — is not an observation and
  keeps its hold, which is `doneWhen`'s road.
- **The watch on a number.** A value is a band collapsed; a number handed in is held to the
  band it falls in, and the number itself stays in the residual the reviewer reads.
- **The reviser waking on every reading.** The seam's docstring named this as its next job;
  a reading inside the prediction is not worth a pass, and one outside says why.
- **Hysteresis in time** ([#615](https://github.com/ShishkinDmitriy/orexis/issues/615)). A
  dwell was proposed so a reading flickering at a boundary would not wake the mind per
  crossing. The width the package types the prediction with does that work and invents
  nothing: a reading at 11.98 against a region starting at 12, with the instrument's noise
  stated, is predicted in BOTH bands and the flip is absorbed. A world stating no noise
  still flips, and then the flip IS a surprise, honestly. Refused; the issue closes here.

# What stays, and why

- **Effects, landings, costs, availability.** What a step makes true is still its declared
  band; a rule reading a reading's number at a node reads the prediction's centre where the
  package wrote one.
- **The residual, suspicion, the remembered plan.** The verdict is the same fact by one road.
- **Every hold that is not a wait for a reading**: plain facts, readiness, `doneWhen`,
  `lapsesAt`, a step's own deadline on the scheduler.
- **The periods table, the door, the forecast.** A prediction is the mechanism the forecast
  already uses, generalised to what the agent predicts of itself.

# The word

"Prediction" is what a package writes about a horizon; "expectation" is the first of them,
the one the next reading is held to; the keeper's row on a step is its **watch**, its stake
in the predictions from the step's landing. `OpenExpectation` and `open_expectations` are
the old rendering's names and go with it.

# What is built, in the order it is built

1. **A prediction is a graph holding during a period, written by its package**
   ([#642](https://github.com/ShishkinDmitriy/orexis/issues/642)): the class, the door, the
   predictor running each package's text at its horizons after every reading, sensing's
   next-reading window first. Additive; nothing in the search reads them yet.
2. **The search reads predictions and computes none**
   ([#643](https://github.com/ShishkinDmitriy/orexis/issues/643)): the overlay at a node's
   instant, the drift and the projected root retired, the crossing generic; #633 lands here.
3. **The expectation is the first prediction, the keeper tells the predictor the intended
   branch, and the verdict comes from the comparison**
   ([#639](https://github.com/ShishkinDmitriy/orexis/issues/639)): the answering shape and the
   set-of-bands words retired.
4. **The reviser wakes on a surprise and a missed window, and on nothing else**
   ([#632](https://github.com/ShishkinDmitriy/orexis/issues/632)); #615 closes on this record.
5. **The word** ([#640](https://github.com/ShishkinDmitriy/orexis/issues/640)).

# Seams left open

- **Nothing dries after a step inside the search.** A dose followed by three hours reads as
  the dosed band until the plan's end; what the world does after the step is predicted once
  the plan is adopted, by the package, from the step's band. The search overrates a step's
  durability by the stretch of its own plan, which is minutes to hours against bands that
  take days; measured before this is believed, in the runbook, when item 2 lands.
- **A package's horizons.** The ladder is the package's; a package listing none predicts
  only the next reading's window. Whether the foresight (`sensing:foresightS`) should bound
  the ladder or the package should is left to the first package that needs a longer one.
- **Two steps landing inside one window.** The intended branch from the last step's landing;
  a plan whose steps land closer than the cadence is judged by its last step.
- **A reading between the taking and the landing** is compared with the do-nothing branch
  and says nothing about the step; a world that answers early is absorbed.
- **Resuming from the branch point** ([#527](https://github.com/ShishkinDmitriy/orexis/issues/527)):
  a surprise now names the step and the band it failed; whether keeping the frontier pays is
  still that issue's measurement.
