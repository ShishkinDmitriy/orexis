---
type: Decision
title: A belief is a crisp triple; sensing and prediction may reason with probability inside, and a want holds the hysteresis
description: >-
  The sovereign challenged the bands on 2026-10-09 - whether sensing's readings and prediction's
  trajectories should be Gaussian rather than intervals. Decided - what enters the belief base is a
  crisp triple, a number, a side, or a band as two numbers, and nothing in it is a probability a
  reader weighs; sensing and prediction are the boundary and may estimate with probability inside,
  a Kalman filter or a least-squares fit, so long as what they write is crisp. The flip of a side on
  a reading's noise is settled by hysteresis held by the want - a desire mints when its range is
  left, a standing want is reached only inside a narrower range - so the sides stay stateless and
  true. Refused - Gaussian beliefs, planning in belief space, hysteresis inside sensing's rules, a
  dwell in time (#615), and a filtered value written over the observation.
status: accepted
timestamp: 2026-10-09T12:00:00Z
---

**Amended by the build (#944), on two points the record had wrong.** The margin between a range and
the narrower one is the reading's whole spread — twice what one reading strays either way, the most
two readings of one value differ by — and not its one-way amplitude, at which a single extreme draw
clears the narrower floor and the chatter resumes a step further up
([narrower-range](/domain/kernel/narrower-range.md)). And a reading near a bound mints and withdraws a
want only where nothing foresees the crossing: measured on the simulator, a bed resting at its floor
minted and withdrew seven wants in thirty readings, while a bed drying through it was held by its
foreseen crossing to one want before the narrower range existed. How a desire names the two tests is
[reached](/domain/planning/reached.md)'s.

# The question

The mind says what it does not know as an interval. A drift that knows its rate only as a range
answers a low and a high rate, prediction carries the [corridor](/domain/prediction/corridor.md)
between them, and a stretch is read at its worst side; membership in a range is crisp. The
sovereign asked whether that was a good choice: whether a reading and a prediction should be
Gaussian instead, a mean and a spread, as a Kalman filter would keep them.

The question turned out to have two halves, and only one of them is about the mind.

# What the tree held, read on 2026-10-09

- **A reading carries no uncertainty at all.** It is a point, `sosa:hasSimpleResult`, and its side
  is a strict comparison in `agent/sensing/rules.ttl` (`FILTER(?value < ?low)`). A probe reading
  0.249 against the terrace bed's floor of 0.25 is below exactly as a noiseless probe would be.
- **A prediction carries worst-case bands**, the corridor, built by interval arithmetic over the
  drifts' rate ranges; an expected value for an uncertain forecast was refused in
  [a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md).
- **Nothing stops a side flipping on noise.** 0.1.0 absorbed a flip by predicting a reading in both
  bands where the world stated an instrument's noise (`sensing:noise`), and #615 was closed on that
  ([the-drift-is-sensings-and-its-result-is-predictions](/decisions/the-drift-is-sensings-and-its-result-is-predictions.md));
  the word was retired with 0.1.0's kernel and 0.2.0 has nothing in its place. Readings of 0.251,
  0.248 and 0.252 read inside, below and inside, and the derivation mints a want and withdraws it.

# The decision

**A belief is a crisp triple.** What enters the belief base is a number, a side, or a band stated
as two numbers, and every reader takes it as true. Nothing in the store is a probability or a
variance that a reader weighs, and the search never ranks a world by likelihood. This is what the
met-tests need: a want is met or not, and a Gaussian handed to a met-test becomes a threshold
anyway — the probability of being below a floor under some bound is the mean less some multiple of
the spread being above it, a band again.

**Sensing and prediction are the boundary, and inside it they may reason with probability.** An
estimator that turns many noisy numbers into one — a Kalman filter over a probe's counts, a
least-squares fit of a bed's drying rate over its series — may keep a mean and a spread while it
works, and should where the noise is characterised and the data are many. What it writes is crisp:
a value or a band, as a revision beside the observation it read, never in place of it, since the
observation is stored because it is the premise
([a-situated-instance-is-kept-only-when-it-is-testimony](/decisions/a-situated-instance-is-kept-only-when-it-is-testimony.md)).
Reflection's estimate of what the mind never measures, which the
[roadmap](/decisions/roadmap.md) already allowed to be Gaussian "since it is a fit over history and
never a belief", is the first such estimator and the same rule.

**A side flipping on noise is settled by hysteresis, and the want holds it.** Two tests, both
stateless:

- a desire **mints** a want when the value leaves its range, as today;
- a standing want is **reached**, and withdrawn, only once the value is back inside a **narrower**
  range the world states.

Which side the agent was on is the want's own existence — minted, it is judged by the narrower test
until reached; not minted, only the range itself can mint one. The sides stay what they are: true
of the reading alone, concluded by rules with no memory. A world that states no narrower range
behaves exactly as it does now. #944 builds it.

# Why

**What bands give up is "likely", and nothing in the mind reads "likely".** A met-test is crisp,
a constraint is crisp, and a world is possible or not. The corridor's worst side already says
"act at the earliest instant the value may cross"; a Gaussian at the same boundary would say the
same thing with a confidence attached that no reader consults.

**The drivers a world states are not Gaussian.** Rain is nought most hours and a burst in others,
and correlated across them; moisture and a battery's voltage are clamped. A Gaussian on either
claims a symmetry the world does not have. A range is what a sovereign can honestly write: "rain is
between nought and two millimetres an hour".

**A spread grows more slowly than a range only for noise.** Independent noise adds as the root of
time, a worst-case range as time itself — but an unknown CONSTANT, a drying rate nobody measured,
spreads linearly under either. What a Gaussian estimator really buys there is learning: data shrink
the spread. That is an estimator's work, inside the boundary, and its output is a narrower band.

**Hysteresis needs no probability.** The margin between the range and the narrower one is the
reading's noise amplitude, a number the world can state from what it measured of its probe; it
needs no distribution behind it.

# What was refused

- **Gaussian beliefs** — a mean and a variance in the store, read by met-tests or a cost as a
  likelihood. They would make every reader interpret a distribution, and every one of them would
  end by thresholding it.
- **Planning in belief space** — searching over distributions of worlds (LQG, belief roadmaps). The
  search is over crisp possible worlds and stays so.
- **Hysteresis inside sensing's rules.** #615 refused it there and the argument stands: a side with
  memory is no longer a conclusion from the reading, and a rule that remembers is a second author of
  a fact the vocabulary concludes.
- **Hysteresis in time, a dwell** — a side counting only once it has held for N readings, which #615
  preferred. It needs no number per boundary, but it delays a REAL crossing by the dwell, and it
  needs a memory of the side somewhere; the want is already that memory and delays nothing at the
  floor.
- **A filtered value written over the observation.** The observation is testimony; a filtered value
  is a conclusion from it and is written beside it.

# Compatible, and named so it is not mistaken for an exception

- **#522's likelihood as expected cost.** A bid's odds of winning, counted from rounds won over
  rounds entered, is a crisp count the agent holds, and a cost text reads it as arithmetic. No
  belief's truth is weighed; the rule above holds.
- **Set-membership estimation** — the interval cousin of a Kalman filter (Schweppe, ~1968; Bertsekas
  and Rhodes, ~1971; Jaulin et al., *Applied Interval Analysis*, ~2001), which intersects a predicted
  interval with a measured one. An estimator may use it as readily as a Gaussian; what leaves is
  crisp either way.

# Seams left open

- **The first estimator in sensing.** A Kalman filter over a probe's counts, writing a steadier
  value beside the observation, is allowed and not built. The trigger is the bench: sides still
  churning near a bound once #944's hysteresis is in, or a reading too noisy to size a dose from.
- **A band an estimator writes says how it was made.** A worst-case band holds the value certainly
  where its premises hold; a band of a mean and some multiple of a spread holds it usually. Should
  an estimator ever write the second kind, the band says which it is, and the multiple — how much
  doubt the agent accepts — would be a [stance](/domain/kernel/stance.md). Nothing writes one yet,
  so nothing is declared.
- **The corridor still treats a range's extreme as certain.** Over a long horizon a wide range of
  rain makes the agent act early. That is the corridor's own seam, and a fitted range from
  reflection is what narrows it.
