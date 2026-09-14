---
type: Decision
title: The drift is sensing's, and its result is predictions the core reads
status: accepted
timestamp: 2026-09-13T20:00:00Z
description: >-
  The sovereign's grooming of 2026-09-13, settled in four exchanges. The drift stays as the
  mechanism and moves out of the core into the sensing package, which runs every drift the
  domain packages declare and writes what comes out as PREDICTIONS — one graph per horizon,
  holding during its window, carrying the predicted reading keyed as the present's and typed
  with every band it may be in, no number crossing any boundary. The core reads predictions
  and computes none: a node's world at an instant is the present with the prediction holding
  then standing in for it, the crossing is the first prediction at which the root reads unmet,
  the expected next observation is the first prediction, and one comparison at arrival is
  every verdict. Retired — the drift run inside the search, the projected root, `orexis:Drift`
  and its rule words in the kernel, `orexis:spreadsBy`, sensing's width arithmetic, the
  set-of-bands predicate, the answering shape built per step, the watch on a number, the
  reviser waking on every reading, and hysteresis in time (#615).
---

# The claim

**The drift is sensing's.** A drift is a package's rule over `$elapsed` — what the world does
to a reading while nobody acts — and a reading is sensing's word, so the machinery that runs
drifts is sensing's too: the vocabulary a domain package declares its drift against
(`sensing:Drift`, its construct, what it replaces, when it crosses), the runner, and the
crossing. The water, climate and market packages declare their drifts against that contract
exactly as they declare their bands against `sensing:InRegion`, which is the shape rule 2
already has: a family's plug-ins import the family's contract. The kernel keeps no
`orexis:Drift`, no `$elapsed`, no drift at a fork and no projected root; it never runs a
rule that knows a rate.

**Its result is predictions.** After every reading, sensing runs each drift at the horizons
the package lists beside it — the next reading's window first, which is where the expected
next observation of #631 goes — and writes one prediction per horizon: a graph holding during
its window (`orexis:PredictionGraph`, a kernel class, so the door knows the kind), carrying
the predicted reading keyed exactly as the present's reading is, typed with EVERY band it may
be in by then, a centre where the package has one. The rate, the spread the world states
beside it and the instrument's noise are inside the package's text; what leaves the text is
bands. A world stating no spread and no noise predicts the one band the rate reaches; the
far horizon predicts every band, which is not knowing said honestly
([a-prediction-is-a-set-of-bands-that-widens-with-the-horizon](/decisions/a-prediction-is-a-set-of-bands-that-widens-with-the-horizon.md)).
A standing step enters the predictions through the keeper — `orexis:predicted`, told when a
watch opens and closes: the step, its band, its landing — and sensing predicts from the
landing on from that band; when the watch closes the do-nothing branch returns.

**The core reads predictions and computes none.** A node's world at an instant is the
present with the path's diffs applied and, for every keyed fact a prediction holding at that
instant carries, the predicted fact in place of the present's — except a key the path itself
changed, because the plan's branch beats the do-nothing branch. Changed is read off the
signature, never off node identity: a dose or a purchase changes its key whichever node it
mints, and a look, which re-stamps the reading it finds and nets to nothing, changes none, so
the prediction stands in for what it looked at. The overlay fills the slot the
drift filled at each fork, so the node's signature, the ground and the cone are untouched —
and a step's own prediction, which the keeper holds the world to, carries none of it: what
the overlay stood in for another reading is the package's promise, not the step's. A
pass for a want met at an instant stands at that instant and reads what is predicted there.
The crossing is generic: an `orexis:At` want is derived at the start of the earliest
prediction at which the root reads UNMET, the root's own met-test asked through the door — a
predicted reading typed with the region band and the one below reads unmet, so the safe
direction ([#633](https://github.com/ShishkinDmitriy/orexis/issues/633)) falls out of the
bands and no kernel line knows a rate.

**One comparison at arrival is every verdict.** When a reading arrives, sensing looks once at
whether it is in the bands the first prediction typed. In them: absorbed — no pass, and a
standing step whose landing has come and whose band it is is MET. Outside them: a surprise —
a pass that names it, and a standing step past its landing whose band it is not is UNMET,
its tail dropped and the failure told upward. The window closing with none: missed — the
reading in hand stale, the freshness want awake, the next prediction what the next reading
is held to. The keeper's watch is band membership, one query over the reading's types
against the step's declared band, not a shape with a value in it. The cone already
identifies the present by the same look (#576).

# What was refused

- **The drift run inside the search.** It was the core computing a rate at every fork; the
  same rule, run by sensing at horizons, is a prediction the core reads. The search stands
  at instants nobody chose, so a prediction holds during a window rather than at a point,
  and the package types it with every band reachable inside the window.
- **A width as a kernel word, and arithmetic in sensing's Python.** `orexis:spreadsBy` handed
  the kernel a number, and sensing summed it with the instrument's noise and mapped a centre
  onto bands by the region's edges — the domain's arithmetic in the wrong place, twice in a
  day. The bands the rule types the reading with are what may leave it.
- **The set-of-bands predicate.** In a predicted world a reading IS every band it may be in,
  and a shape refusing one refuses the world; `sensing:mayBe` would need the kernel to
  translate a sensing word, and `rdf:type` is what every rule already reads.
- **The answering shape built per step, and the watch on a number.** A SHACL shape with a
  value in it, compiled and held on the step, was a second rendering of the prediction with
  a blind spot the suite found: a node stating no value passes a constraint on a value.
- **The reviser waking on every reading.** A reading inside the prediction is not worth a
  pass; one outside says why.
- **Hysteresis in time** ([#615](https://github.com/ShishkinDmitriy/orexis/issues/615)). A
  reading at 11.98 against a region starting at 12, with the instrument's noise stated, is
  predicted in both bands and the flip is absorbed; a world stating no noise flips, and then
  the flip is a surprise, honestly. Closed on this record.

# What stays, and why

Effects, landings, costs and availability, which read a predicted reading at a node as they
read the present's. The residual, suspicion and the remembered plan: the verdict is the same
fact by one road. Every hold that is not a wait for a reading. The periods door and the
forecast, which a prediction generalises to what the agent predicts of itself.
`sensing:noise` and `water:driesPerDaySpread` as facts the package's rule reads.

# The word

A **prediction** is what sensing writes about a horizon; the **expectation** is the first of
them, the one the next reading is held to; the keeper's row on a step is its **watch**, its
stake in the predictions from the step's landing. `OpenExpectation` and `open_expectations`
are the old rendering's names and go with it.

# What is built, in the order it is built

1. **The drift moves to sensing and writes predictions**
   ([#642](https://github.com/ShishkinDmitriy/orexis/issues/642), built): sensing's runner
   (`predictions.py`), the water drift typing its prediction with every band it may be in,
   `orexis:PredictionGraph` and the door, one graph per horizon — the drift's vocabulary
   stays `orexis:Drift` for this one step, since the kernel still runs it at forks and moves
   with it in #643 —
   after every reading with the next window first; `orexis:spreadsBy`, sensing's arithmetic
   and #631's `ExpectedObservation`, `mayBe` and `ExpectationsGraph` retire, and so do the
   staleness horizon and its timer — the first prediction's end is the horizon, and a window
   closing with no reading writes `staleSince`
   ([a-root-holds-always-and-an-outdated-graph-is-dropped](/decisions/a-root-holds-always-and-an-outdated-graph-is-dropped.md)).
   The kernel still runs its own drift at forks for this one step, so every world's plans
   are unchanged. Before it, the clock
   ([#646](https://github.com/ShishkinDmitriy/orexis/issues/646),
   [the-agent-keeps-one-timeline-and-its-clock-may-run-fast](/decisions/the-agent-keeps-one-timeline-and-its-clock-may-run-fast.md))
   and the roots authored at genesis ([#644](https://github.com/ShishkinDmitriy/orexis/issues/644)),
   since every measurement after depends on the first and the child's derivation on the second.
2. **The search reads predictions and computes none**
   ([#643](https://github.com/ShishkinDmitriy/orexis/issues/643), built): the overlay at a
   node's instant — a key the path changed excepted, in the signature's words — in the slot the drift filled; the
   kernel's drift, projected root, `orexis:Drift` and `orexis:crossesAfter` retired, the word
   sensing's; the crossing generic, the start of the earliest prediction at which the root
   reads unmet, so #633 lands here and a crossing's resolution is the package's ladder; and
   one point found wanting on the way, `orexis:repredict`, told by whoever moves a premise a
   drift reads — the ledger, first — so a crossing the ledger creates is seen before the
   next reading.
3. **The keeper tells sensing the intended branch, and the verdict comes from the comparison**
   ([#639](https://github.com/ShishkinDmitriy/orexis/issues/639)).
4. **The reviser wakes on a surprise and a missed window, and on nothing else**
   ([#632](https://github.com/ShishkinDmitriy/orexis/issues/632)).
5. **Every want sourced at a time as a graph with a period, and one sweep**
   ([#645](https://github.com/ShishkinDmitriy/orexis/issues/645)).
6. **The word** ([#640](https://github.com/ShishkinDmitriy/orexis/issues/640)).

# Seams left open

- **Nothing dries after a step inside a pass.** A dose followed by three hours reads as the
  dosed band until the plan's end; what the world does after the step is predicted once the
  plan is adopted, from the step's band. The search overrates a step's durability by the
  stretch of its own plan, minutes to hours against bands that take days; measured in the
  runbook when item 2 lands, before it is believed.
- **A package's horizons.** The ladder is the package's; a package listing none predicts
  only the next reading's window, and whether `sensing:foresightS` should bound the ladder
  is left to the first package that needs a longer one.
- **Two steps landing inside one window** are judged by the last step's band.
- **A reading between the taking and the landing** is compared with the do-nothing branch
  and says nothing of the step; a world that answers early is absorbed.
- **Resuming from the branch point** ([#527](https://github.com/ShishkinDmitriy/orexis/issues/527)):
  a surprise now names the step and the band it failed; whether keeping the frontier pays
  is still that issue's measurement.
