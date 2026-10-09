---
type: Decision
title: A belief is a crisp triple; sensing and prediction may reason with probability inside, and sensing holds the hysteresis
description: >-
  The sovereign challenged the bands on 2026-10-09 - whether sensing's readings and prediction's
  trajectories should be Gaussian rather than intervals. Decided - what enters the belief base is a
  crisp triple, a number, a side, or a band as two numbers, and nothing in it is a probability a
  reader weighs; sensing and prediction are the boundary and may estimate with probability inside,
  a Kalman filter or a least-squares fit, so long as what they write is crisp. The flip of a side on
  a reading's noise is settled by hysteresis in sensing - a range's condition states one margin, a
  reading judged below stays below until it clears the floor by it, and the side the reading before
  was judged on is carried onto the observation by its writer, so no rule remembers. The words are
  sensing's, and a prediction reads none of them, a predicted number having no instrument's noise.
  Amended the same day from a hysteresis held by the want, refused with a narrower second range, the
  last N observations, and the margin's words in the kernel for prediction to read. Refused -
  Gaussian beliefs, planning in belief space, a rule that remembers, a dwell in time (#615), and a
  filtered value written over the observation.
status: superseded-in-part
superseded-by: an-observation-is-a-percept-and-the-mind-reads-only-beliefs
timestamp: 2026-10-09T12:00:00Z
---

> **Superseded in part, 2026-10-09: the hysteresis is belief revision's, held by the belief.** What a
> belief is — a crisp triple, with probability only inside an estimator — stands. Where a side is
> held does not: [an-observation-is-a-percept-and-the-mind-reads-only-beliefs](/decisions/an-observation-is-a-percept-and-the-mind-reads-only-beliefs.md)
> makes an observation a percept the mind never reads, and a state is held by revision judging a
> percept beside the belief it replaces. The side carried onto the observation and the predicted
> number judged bare, both below, are refused there.

> **Amended 2026-10-09 (#944): the hysteresis is sensing's, and the want holds none of it.** As first
> decided, a desire minted a want where its range was left and a standing want was reached only inside
> a narrower range the world stated, so the sides stayed a bare comparison and the want's existence was
> the memory. That was built, and the sovereign refused it the same day: planning works on crisp
> triples and does not decide whether a value is inside a range — sensing does, so the hysteresis is
> sensing's. A range's condition states ONE number, its margin
> (`sensing:margin`); a reading judged below stays below until it reaches the floor and the margin, one
> judged above stays above until the ceiling less it, and one coming from inside crosses at the bound
> itself. The memory that needs is the side the reading before was judged on, carried onto the new
> observation by `received` (`sensing:wasBelow`, `sensing:wasAbove`) exactly as it carries the run of
> an unchanged number (`sensing:unchangedSince`), and the side rules read the observation's own facts
> and remember nothing. The three words were first declared in the kernel, so that prediction could
> place a crossing out of a side at the bound and its margin and carry each stretch's side; the
> sovereign refused that too, the kernel speaking no SOSA or SSN, and the words are sensing's.
> Prediction reads no margin: a predicted number carries no instrument's noise. Planning is untouched.
> The body below is amended to that; what was refused, and what the refused builds measured, are in
> their own sections.

# The question

The mind says what it does not know as an interval. A drift that knows its rate only as a range
answers a low and a high rate, prediction carries the [corridor](/domain/prediction/corridor.md)
between them, and a stretch is read at its worst side; membership in a range is crisp. The
sovereign asked whether that was a good choice: whether a reading and a prediction should be
Gaussian instead, a mean and a spread, as a Kalman filter would keep them.

The question turned out to have two halves, and only one of them is about the mind.

# What the tree held, read on 2026-10-09

- **A reading carries no uncertainty at all.** It is a point, `sosa:hasSimpleResult`, and its side
  was a strict comparison in `agent/sensing/rules.ttl` (`FILTER(?value < ?low)`). A probe reading
  0.249 against the terrace bed's floor of 0.25 was below exactly as a noiseless probe would be.
- **A prediction carries worst-case bands**, the corridor, built by interval arithmetic over the
  drifts' rate ranges; an expected value for an uncertain forecast was refused in
  [a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md).
- **Nothing stopped a side flipping on noise.** 0.1.0 absorbed a flip by predicting a reading in both
  bands where the world stated an instrument's noise (`sensing:noise`), and #615 was closed on that
  ([the-drift-is-sensings-and-its-result-is-predictions](/decisions/the-drift-is-sensings-and-its-result-is-predictions.md));
  the word was retired with 0.1.0's kernel and 0.2.0 had nothing in its place. Readings of 0.251,
  0.248 and 0.252 read inside, below and inside, and the derivation minted a want and withdrew it.

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

**A side flipping on noise is settled by hysteresis, and sensing holds it.** Whether the subject is
below its range is sensing's judgment — it reasons inside the boundary and writes a crisp side — so
the hysteresis is in that judgment and nowhere downstream of it:

- a range's condition states one **margin**, the same at the floor and the ceiling;
- a reading coming from inside is judged at the bound itself, so a real drop reads below at once;
- a reading whose predecessor was judged below stays below until it reaches the floor and the
  margin, and one judged above stays above until it falls to the ceiling less the margin.

Which side the reading before was on is carried onto the observation by `received`, the writer, as
it carries `sensing:unchangedSince`: the previous observation's side summarises its whole history,
as a Schmitt trigger's state is its output, and one timestamp already summarises an unbroken run of
one number. The rules read the observation's own facts — the reading, the bounds, the margin, the
side carried — and keep no state. A range that states no margin behaves exactly as it did, and a
want, a desire and the search are as they were.

**A prediction reads no margin, and the words are sensing's.** Hysteresis corrects the instrument's
noise, a reading wobbling about a bound; a predicted value is the model's number, and its doubt is
the corridor. So prediction places a crossing at the bare bound and writes a predicted observation
carrying no side, and the rules judge it by its number alone. `sensing:margin`, on a range's
condition, and `sensing:wasBelow` and `sensing:wasAbove`, on an observation, are read by sensing's
rules and `received`, and by onboarding, which refuses a margin its range cannot hold.

What that costs, measured on the greenhouse at rest in #946's build: a
reading held below inside the margin, 0.3001 against a floor of 0.30, is predicted inside while the
present reads below. The want is minted by the present and kept by it; nothing the stretch ahead
reads withdraws it or mints it again. The planner believes the stretch ahead: holding no pump, it
commits a `planning:Wait` toward it, the wait lands, the want still stands, and another is committed
— three in an hour of readings held at 0.3001, twelve in thirty cadences of the noisy simulator over
a bed resting at 0.3005, where the build that held the stretch ahead below committed none. Each
sends nothing. Holding a pump, the grower doses as that build did, four doses in that hour and no
wait.

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

**Hysteresis needs no probability.** The margin is the reading's noise — its whole spread, twice what
a reading strays either way — a number the world can state from what it measured of its probe; it
needs no distribution behind it.

**One number goes wrong in fewer ways than two.** A margin is a figure beside the bounds it widens;
whether it is sane is one comparison with half the range's width, and `orexis-onboard` makes it.

**A predicted number has no noise to hold a side against.** A margin is sized from what an
instrument strays; the model's number strays by nothing, and how much the agent does not know about
it is the corridor's width, which leaves prediction as a worst side and never as a widened number.
Holding a predicted stretch on a side by a margin made prediction walk the corridor from the
observation's side with a trigger kept in Python — a second judge of a side the rules already judge.

# What the refused build measured

The hysteresis held by the want was built in full before it was refused, and two of its findings
stand whichever package holds the hysteresis; both were measured again on the build that
held it in sensing (#946).

- **The margin is the noise's WHOLE spread**, twice what a reading strays either way. A value resting
  exactly at the floor is read anywhere within the noise on either side of it, so a margin of the
  one-way figure is cleared by one extreme draw of a value that never moved.
- **A drying bed did not chatter before either.** A want minted for a foreseen crossing is weighed at
  its instant, and a desire reading unmet at a ground ahead keeps it whatever the present reads: the
  greenhouse's bed drying a hundredth a day through its floor, its probe straying 0.002 either way,
  crossed the floor nineteen times in fifteen hours and was one want with no margin at all. The
  chatter is a bed at rest at its floor — the same probe over a bed resting at 0.3005 minted seven
  wants and withdrew seven where a margin of 0.004 mints one — or a want rooted in the present.

# What was refused

- **Gaussian beliefs** — a mean and a variance in the store, read by met-tests or a cost as a
  likelihood. They would make every reader interpret a distribution, and every one of them would
  end by thresholding it.
- **Planning in belief space** — searching over distributions of worlds (LQG, belief roadmaps). The
  search is over crisp possible worlds and stays so.
- **Hysteresis held by the want** — this record's first decision: a desire minting where its range is
  left, and a standing want reached only once its value is back inside a narrower test, a second
  shape per desire (`planning:reachedWhen`). Built and refused on 2026-10-09. Planning works on crisp
  triples and does not decide whether a value is inside a range; and a second shape per desire is a
  second met-test, which drifts from the first as two ranges do.
- **The margin's words in the kernel, for prediction to read.** Built and refused on 2026-10-09: the
  margin and the two sides carried, declared in the kernel's namespace under `sosa:` and
  `ssn-system:` prefixes it had never bound, because prediction placed a crossing out of a side at
  the bound and its margin and wrote each stretch's side, and prediction's layout forbids sensing's
  words. The kernel speaks no SOSA or SSN — `sosa:` reaches a query because sensing's ontology
  declares it, not because the kernel knows what a reading is (#378) — so a word about a
  `ssn-system:Condition` or a `sosa:Observation` is sensing's; and prediction needed none of it.
  Carrying the side onto a predicted reading without the margin is no middle way: the rules would
  hold below a number prediction had placed inside, and the two would disagree about where a stretch
  begins.
- **A second, narrower range per subject.** Two ranges give many ways to go wrong — a narrower range
  not inside its wider one, inverted, one side forgotten, the two edited apart — where one number
  does not.
- **The last N observations kept.** The side of the observation before already summarises the whole
  history, and `sensing:unchangedSince` summarises an unbounded run in one timestamp; N observations
  would make the belief base a short series — and a series is watched, never believed — and make
  "the present reading" ambiguous for every reader of it.
- **A rule that remembers.** #615 refused hysteresis held in a rule's memory, and the refusal stands
  and is honoured: a side concluded from what the rule recalls is no longer a conclusion from the
  observation, and a writer that wrote a side would be a second author of a fact the vocabulary
  concludes. Here the side carried is a premise on the observation, written by the writer beside the
  number as the run is; the side is concluded by the rules alone, from that observation's facts.
- **Hysteresis in time, a dwell** — a side counting only once it has held for N readings, which #615
  preferred. It needs no number per boundary, but it delays a REAL crossing by the dwell, and it
  needs a memory of the side somewhere; the side carried is that memory, and a margin delays nothing
  coming from inside.
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
  churning near a bound under a margin, or a reading too noisy to size a dose from.
- **A margin no probe's spread was measured for.** The terrace's probe is the coarsest in the tree
  and states none: it holds no desire, and nothing measured how far its count strays. The trigger is
  the terrace holding a desire.
- **A band an estimator writes says how it was made.** A worst-case band holds the value certainly
  where its premises hold; a band of a mean and some multiple of a spread holds it usually. Should
  an estimator ever write the second kind, the band says which it is, and the multiple — how much
  doubt the agent accepts — would be a [stance](/domain/kernel/stance.md). Nothing writes one yet,
  so nothing is declared.
- **The corridor still treats a range's extreme as certain.** Over a long horizon a wide range of
  rain makes the agent act early. That is the corridor's own seam, and a fitted range from
  reflection is what narrows it.
