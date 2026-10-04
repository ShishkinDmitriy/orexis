---
type: Decision
title: A prediction accumulates rates between happenings, inside a corridor
status: accepted
timestamp: 2026-09-28T12:00:00Z
description: >-
  The sovereign's model of prediction, agreed 2026-09-28 while asking how a terrace would learn
  when rain waters it. A drift answers a RATE, the rate of its property at an instant, and every
  drift moving one property adds to it; the prediction package accumulates the sum between
  HAPPENINGS, the instants any graph a drift may read begins or ends, re-reading every hour,
  and places each crossing of a range bound exactly. A rate known only as a range gives a
  CORRIDOR, the lowest and highest trajectory, and the stretch's side is the corridor's worst.
  It is PDDL+'s trajectory semantics, a process per drift and a timed fluent per forecast, and
  it stays below the search, which is still qualitative. Refused - the fixed ladder and its
  bisection, a drift answering the value it reaches, a stored net rate and an expected value.
---

# The claim

**A drift answers a rate, and rates add.** `prediction:Drift` carries `prediction:rate`, a select
answering how fast the property it `prediction:moves` is changing, per second of the one timeline,
for `$feature` holding `$value` at `$at`. Drying is one drift and rain another; neither knows the
other exists, and the rate the value moves by is their sum. A drift that stops somewhere says so,
`?until`, and contributes nothing past it: the soil dries until nothing is left and wets until it
is saturated.

**What is stored is what the world states; the net rate is computed and never written.**
`climate:driesPerDay` is a rate, and it is stored, because it is a constant of the bed. What is
never stored is the rate the value actually moves by at an instant, because it depends on what
holds then: a forecast hour, and a committed step. The drift reads both and answers; the
package sums and accumulates; only the stretches are written.

**Time is split at the happenings.** A happening is an instant at which what a drift reads may
change: the start or end of any public or belief graph holding inside the horizon, which is how a
forecast hour and a committed step's landing window become one without prediction learning a word
of either. Between two happenings the rates are asked once and held, at most for an hour, so a rate
that depends on the value is asked again; within a segment the value is linear, and a crossing of
a range bound is placed exactly, `(bound − value) / rate`. The horizon is a day past the
observation.

**A range of rates gives a corridor.** A forecast of nought to two millimetres an hour is a rate
known as a range, and ranges add as rates do, `[a,b] + [c,d] = [a+c, b+d]`. Accumulated, they give
the [corridor](/domain/prediction/corridor.md): the lowest and the highest trajectory the value may
follow. The side of a stretch is the corridor's worst - below where the low trajectory is under a
floor, above where the high one is over a ceiling - and the number written is that trajectory's,
so sensing's rules conclude of it exactly the side the corridor has. A want is then minted at the
earliest instant the value MAY cross, which is the safe side, and "do not water" is said only when
even the dry end of the forecast keeps the soil inside.

# PDDL, term for term, continued

The 0.1.0 table ([an-always-want-is-a-root…](/decisions/0.1.0/an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it.md))
stopped at PDDL 2.2. PDDL+ (Fox and Long, JAIR 2006) is where continuous change lives, and its
semantics are adopted for prediction as they stand.

| PDDL+ | here |
|---|---|
| a process, `(increase (v) (* #t rate))` while its condition holds | a drift, its `prediction:rate` |
| processes on one fluent sum | the drifts moving one property add |
| an event, fired when its condition becomes true | a crossing, which `lay_ground` calls an action nobody takes |
| a timed initial fluent (2.2's literals, numeric) | a forecast hour: a graph holding during its period |
| a happening | a happening: a graph's period beginning or ending |
| the trajectory between happenings | the stretches, one prediction per side |
| discretise-and-validate at a step δ (UPMurphi, DiNo, ENHSP) | the ladder this replaces |
| exact linear change between happenings (COLIN, POPF) | a crossing placed by division |

Naming PDDL+ is not proposing to parse it, and no planner is adopted.

# The search stays qualitative

PDDL+ keeps its numbers in the search; this does not.
[deliberation-is-on-triples-and-a-number-is-not-special](/decisions/deliberation-is-on-triples-and-a-number-is-not-special.md)
stands whole: the domain describes its world in ranges, the core compares triples, and the
command sizes the act from the present when a step is taken. The name for that split is
qualitative reasoning - Forbus's Qualitative Process Theory and Kuipers's QSIM: a quantity space of
landmarks, which are the range bounds, a state that is the interval a value is in, and limit
analysis, which is the crossing. What prediction adds is the number that says WHEN a landmark is
reached, and nothing numeric leaves it but the stretch. That is what keeps the worlds few: every
value inside a range is one world, and a forecast of twenty-four hours lays grounds only where rain
flips a side, not one per hour. How many landmarks a property has is the world's to decide, and
more of them is finer foresight bought with more worlds.

# What was refused

- **The fixed ladder and its bisection.** Rungs at an hour, five and a day found a crossing only
  where the two ends of a rung disagreed, so a value that dipped below a floor and came back inside
  one rung was never seen - which is exactly what rain does to a drying bed. Drying alone is
  monotone and hid it. A happening is where a rate may change, so a crossing between two is on a
  straight line and no scan is needed to find it.
- **A drift answering the value it reaches.** A drift that answered the observation `$elapsed`
  seconds on could not be combined: two drifts answered two numbers for one node and the first was
  taken. Rates add; values do not.
- **One drift for the whole water balance.** It would compose by hand what the sum composes, and
  every domain adding a flow - a leak, a committed dose - would edit it.
- **A stored net rate.** It is a conclusion whose premises are stored and would outlive them
  (a-situated-instance-is-kept-only-when-it-is-testimony).
- **An expected value for an uncertain forecast.** Amount times probability is the number no
  trajectory takes; the corridor keeps both ends, which is how this project says it does not know.

# Seams left open

- **The corridor leaves prediction as one number.** The planner reads one prediction per stretch,
  so a corridor that straddles a bound is written as its worst side and not as "may be either"; the
  0.1.0 set of bands is what carrying both would look like. A corridor below one range's floor and
  above another's ceiling at once writes the floor's side.
- ~~Committed steps are not yet flows~~ - closed by #849, 2026-10-03, as this seam said it would be:
  the executor writes each step of an adopted plan into the beliefs as a
  [committed step](/domain/execution/committed-step.md), a graph holding over its landing window, so
  the window's ends are happenings and a drift reads the step at an instant inside it; the actuation
  domain's `actuation:Dosed` answers the dose's rise over the window, the low trajectory by the latest
  landing, so a late landing widens the corridor. A later want is searched against a future that
  contains the earlier plan, which is the IRMA order (Bratman, Israel and Pollack, 1988): a
  commitment is background a new option is filtered against, earliest committed first. Two plans
  drawing one barrel still interfere only where a drift of the barrel's level reads the committed
  draws; no shipped world observes a source's level yet. A step no drift will ever read — a
  fictive one, a drive — is laid as its own prediction instead, decided 2026-10-04
  ([a-desire-bounds-the-search-and-a-plan-found-is-the-ground-of-the-next](/decisions/a-desire-bounds-the-search-and-a-plan-found-is-the-ground-of-the-next.md)).
- **A possible world is judged in the ground at its earliest landing, not in every ground its
  landing overlaps.** Since 2026-10-03 a world holds over the period its path's landing bands sum
  to, and since 2026-10-04 it is forked from the ground holding at its earliest landing with the
  path replayed there
  ([a-landing-is-a-band-and-a-world-holds-over-a-period](/decisions/a-landing-is-a-band-and-a-world-holds-over-a-period.md));
  judging a landing that straddles a boundary in every ground it overlaps is strong controllability
  over an STNU (Morris, Muscettola and Vidal, 2001), and is the part of
  [#596](https://github.com/ShishkinDmitriy/orexis/issues/596) still open.
- **A driver has no level form.** Outside temperature is not a stock; its forecast IS its future,
  and a key the agent observes that follows a forecast would be a drift answering a level rather
  than a rate. Nothing reads one yet.
- **No forecast arrives.** A forecast graph is written by hand in a test; the fetcher is a
  transport member the runtime cannot yet hold beside MQTT.

# What it amends

[the-drift-is-sensings-and-its-result-is-predictions](/decisions/the-drift-is-sensings-and-its-result-is-predictions.md),
in its 0.2.0 amendment: the drift is still prediction's and its result is still one prediction per
stretch; what `predict` does between is accumulation over happenings rather than a ladder and a
bisection, and a drift answers a rate.
