---
type: Decision
title: A prediction is a set of bands that widens with the horizon, and an event is expected in a window
status: accepted
timestamp: 2026-09-13T12:00:00Z
description: >-
  The sovereign, 2026-09-13, on reading the arrivals PR. Two things the bundle had half of. A
  STATE holds during a stretch and an EVENT does not, so a predicted state is a graph with a
  period and a predicted event is a fact about the window it is expected in — an observation
  is an event, and the next one can be expected from the cadence and the drift. And a
  prediction is always bands, never a value — a value is a band collapsed — and the further the
  horizon the wider the set, until it is every band. Refused — a numeric spread in the core, a
  point prediction, a fixed width, and the periods table as the home of an event's window.
  Built: the expected next observation (#631), the crossing in the safe direction (#633,
  inside #643), the intended branch (#639) and the reviser waking on a surprise rather than
  on a reading (#632). All four items are built.
---

# The claim

**A state is stretched in time and an event is not.** A fluent holds during a period, and the
period belongs to the graph it is said in
([a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md)). An event
occurs at an instant; before it occurs, what is known is the WINDOW it is expected in, and
after, the instant it occurred at. So a predicted state is a graph with a period, and a
predicted event is an expected occurrence — a fact about its window, stated inside a graph
whose own period says how long the expectation is worth believing. The two must not share a
mechanism: a graph scoped by the window would answer a question about one instant with a
claim about the stretch, which is the mistake #613 caught in a filed issue.

**An observation is an event.** `sosa:resultTime` is its instant once it has occurred. The
next one can be expected: the instrument's cadence says when, and the [drift](/domain/effect.md)
applied over that stretch to the reading in hand says what. Both halves exist today and are
not joined.

**A prediction is always a set of bands, never a value.** A value is a band collapsed to a
point, and a reading carrying one is a set with one member. This is the ruling that took
numbers out of imagined worlds, applied to what is expected rather than what is planned: the
core compares bands, the domain keeps the arithmetic, and "0.4 plus or minus 0.05" is the
domain's way of choosing which bands the set holds.

**The further the horizon, the wider the set.** Now the reading is in its region, and the
instrument's own noise is the width; in an hour the rate's uncertainty has added to it; in
five the set may hold the region and the band below; in a day it holds every band, which is
the honest statement that the agent knows nothing that far out. The two-cones record said this
as a NARROWING set — a forecast three days out is every band, tonight two, now one — and it is
the same shape read from the present outward. The width is the domain's to state: the
instrument's noise beside the instrument, the rate's uncertainty beside the rate, neither in
the core.

**An intention changes the prediction.** The sequence of expected observations is a discrete
rendering of the formula the drift is, and it is the world's own branch — what happens if
nothing is done. An adopted plan is the agent choosing another branch, so the sequence past
each step's landing is the step's predicted band, which the keeper already holds the world to
as the step's expectation, and the drift runs on from there. That is the two cones joined at
one seam: the belief cone's next node is the drift's until an intention stands and the
intended branch's after, and a surprise is a reading outside whichever the agent is on. The
keeper's expectation on a step's end and the expected next observation are then one kind of
fact, and the second is what remains when no step is pending.

**Three things follow.**

- The reviser's filter. A reading that lands inside its expected set is the world going on as
  believed and wakes nothing; one outside is an exogenous surprise, caught at arrival rather
  than at the next pass, and the pass it wakes says so. This is the "bands, not raw values"
  filter the reviser's docstring names as its next job, and it is the better answer to the
  deliberation storm than #615's dwell, because it wakes on contradiction rather than on time.
- Staleness is a missed expected event. A reading that does not land in its window is what the
  freshness want and its horizon have been saying; said once, as the expectation lapsing,
  which is where #331 and #348 point.
- The crossing a root foresees is the first horizon at which the set no longer holds the
  region band, not the instant the nominal rate reaches the floor. Not knowing is maximal, so
  the safe direction is to act when the region MAY be left. A world stating no width keeps
  the nominal crossing, which is the set with one member.

# What was refused

- **A numeric spread in the core.** The interval record was built and refused once; a plus or
  minus on a prediction is the same interval under another name, and the search would have
  to compare it. The set of bands is what the search reads, and the width lives where the
  number does, in the domain's measure.
- **A point prediction.** A value with no width claims more than any instrument can, and a
  surprise judged against it fires on every reading. The degenerate set is legitimate; the
  bare value is not.
- **A fixed width.** The sovereign's own numbers widen fourfold from one hour to five; a
  constant band would be wrong at one end or the other.
- **The periods table as the home of an event's window.** That table says which stretch a
  graph speaks for, and the saying stays beside the said. An expected event's window is a
  fact about the event, inside the graph.

# What follows, in the order it would be built

The mechanism was groomed the same day, once item 1 stood beside the keeper's watch:
[the-drift-is-sensings-and-its-result-is-predictions](/decisions/the-drift-is-sensings-and-its-result-is-predictions.md)
moves the drift into sensing and makes its result predictions the core reads — graphs
holding during windows, typed with every band the reading may be in — and items 2 and 3
are built under it (#642, #643, #639, #632).

1. Sensing writes the expected next observation after every reading
   ([#631](https://github.com/ShishkinDmitriy/orexis/issues/631), built): the window from the
   cadence in force and the grace the freshness horizon already uses, the bands from the
   drift's centre at the window's far end — read through the rules' own door as the planner
   reads a drift — widened by the instrument's `sensing:noise` and by what each drift's
   the rate's spread states over the stretch, typed onto the subject's own bands inside the
   drift's own rule since #642 (`orexis:spreadsBy` and the set-of-bands words retired); into a
   working graph of the agent's own (`sensing:ExpectationsGraph`, never carried into a
   plan's imaginarium — carried, it re-grounded the cone at every reading), the window as `dcterms:temporal`
   on the node, the bands as `sensing:mayBe`; replaced by the next reading, gone when the
   window closes with none. The world stating no width gets one member, and every world's
   plans are unchanged. Where an intention stands, the expectation past a step's landing is
   the step's own: built as #639, below.
2. The reviser wakes the mind on a surprise, not on a reading
   ([#632](https://github.com/ShishkinDmitriy/orexis/issues/632), built): a reading inside
   the bands the first prediction typed is absorbed, one outside wakes a pass that names the
   surprise (`reviser.observed`, sensing handing it the two sets), a missed window takes the
   freshness path, and the actuator's mark on every reading retired with it.
3. The crossing is taken in the safe direction
   ([#633](https://github.com/ShishkinDmitriy/orexis/issues/633), built inside #643): the
   crossing is the start of the earliest prediction at which the root reads unmet, and a
   prediction typed with the region band and the one below reads unmet.
4. The intended branch ([#639](https://github.com/ShishkinDmitriy/orexis/issues/639), built):
   the keeper tells sensing the band a standing step declared and when it lands; from the
   landing on the predictions of the key are that band, and a reading is compared with it
   once at arrival for the verdict.

# Seams left open

- **The intended branch's centre.** From a step's landing the prediction is the step's
  band with the number the actor aimed at where it stated one, and no number otherwise; a
  drift run from the band would need a centre a band does not have.
- **The window's far end is the width's horizon.** The set is widened at the instant the
  grace runs out, the widest the window reaches: the safe direction, and a reading arriving
  early is judged against a set slightly wider than its own instant warrants.
- **The rate's uncertainty is the world's fact.** Review moves the agent's beliefs, and a run
  of surprises against a stated rate says the rate is wrong; whether review may move a world
  fact is the question #607 left, still open.
- **The time band of a scheduled instrument.** The window of the next reading is the cadence
  plus a grace; the window of the fifth one out is wider only if the cadence drifts, and no
  shipped instrument's does.
- **A forecast's own width.** A service's forecast arrives as bands already; whether it should
  arrive as a widening sequence is the service's to say.

# Amended 2026-09-24: in Agent 0.2.0 a prediction is a number per stretch

The set of bands stands for the 0.1.0 tree. In `agent/sensing/` a prediction carries the
number the drift gives, one prediction per stretch between the instants the reading changes
range, and the side of it is a [revision](/domain/revision.md) the rules sensing registers
conclude; the widening set is what the rules would conclude of each stretch, and no band is
written by sensing. The window an event is expected in is unchanged. See
[prediction](/domain/prediction.md).
