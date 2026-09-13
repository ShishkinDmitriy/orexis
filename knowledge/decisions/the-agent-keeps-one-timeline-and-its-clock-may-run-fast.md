---
type: Decision
title: The agent keeps one timeline, and its clock may run fast
status: accepted
timestamp: 2026-09-13T22:30:00Z
description: >-
  The sovereign's ruling of 2026-09-13, refusing the-world-states-the-length-of-its-day the
  day it was built: an agent does not know how many seconds an hour has, and a mind that reads
  a unit off the world has two timelines. There is ONE timeline. Every instant the agent
  writes and every stretch it keeps — a reading's instant, a period, a cadence, a landing, a
  day of drying — is in it, and a compressed world is not a fact the rules read but a CLOCK
  that runs fast: the runtime's clock, paced by a deployment fact handed to every process of
  the world alike, agents and stand-ins, so a day is eighty-six thousand four hundred of the
  agent's seconds wherever it runs. Refused — a length of day the mind reads, physics on one
  clock and devices on another, and rates restated in the agent's clock.
---

# The claim

**One timeline.** An agent writes instants — a reading's `resultTime`, a period's start and
end, a want's `holdsAt`, a step's `notBefore`, a debt's expiry — and keeps stretches — a
cadence, a grace, a patience, a landing, the `$elapsed` a drift is handed — and every one of
them is in the same timeline. A day is eighty-six thousand four hundred seconds of it, an hour
three thousand six hundred, and a rule may say so: the literal is not a unit the mind learned,
it is the timeline's own arithmetic. Nothing in the mind, the packages or the rules knows a
second timeline exists.

**The clock is the runtime's, and it may run fast.** Progression is the layer that keeps time
(the scheduler sleeps until the next deadline and runs nothing), so the clock is its: one
`now()` every layer and package reads instead of the wall clock, and one conversion where a
sleep is real — a delay of so many of the agent's seconds is that many real seconds over the
PACE. The pace is a deployment fact, not a belief: environment, handed to the container as
the world's directory is (rule 5), and the mind cannot ask for it. A world that compresses
time states its pace once, on its world node, for the substrate — `sim:timeScale`, as before —
and compose hands the same figure to every process of that world alike: the agents' clocks
and the stand-ins' physics, ticks and pours. A stand-in that sleeps a cadence the agent asked
for sleeps that many of the world's seconds, converted at the sleep exactly as the agent's
scheduler converts. The timeline is continuous across restarts because its origin is fixed:
an epoch stated with the pace, so a restarted agent's `now()` lands where the world's clock
stands and every instant it wrote before still means what it meant.

**What this answers.** The world file's own worry — "a dose sized for a day's drying would
land against an hour's" — was two clocks in one world: physics compressed, devices real. On
one clock a pour of nine hundred seconds is nine hundred of the world's seconds, a cadence of
six hundred is six hundred, a day is a day, and the agent's prediction and the stand-in's
physics agree without either knowing the pace. The bench then shows what the rule says: the
fern at 0.47 crosses in four of the world's hours, which is a hundred bench seconds, and the
agent foresees it, buys ahead and places the presenting inside them. And a test may run its
agent on a fast clock and watch a day pass in a second.

# What was refused

- **A length of day the mind reads** ([#647](https://github.com/ShishkinDmitriy/orexis/pull/647),
  closed unmerged). `orexis:secondsPerDay` on the world node, derived where absent, read by
  every rule that turns a rate into a stretch: it made the agent know how many seconds its
  hour had, which is to know two timelines and convert between them in every rule, and it
  left cadences, pours and landings on the other clock. "It requires knowing real time and
  not-real time."
- **Physics on one clock and devices on another.** The stand-ins scaled their physics by the
  pace and kept their ticks and pours real, and the agent's timers were real; the agent's
  predictions were a hundred and forty-four times too slow and no plant could buy ahead. One
  clock for every process of a world, converted only where something actually sleeps.
- **Rates restated in the agent's clock.** A pot drying seventeen times a real day would make
  "day" mean nothing in the file the sovereign writes.

# What is built

[#646](https://github.com/ShishkinDmitriy/orexis/issues/646), built: `orexis_agent_progression.clock`
— `now()`, `pace()`, `real_delay()`, `monotonic()` — with its pace and epoch from the
environment; every wall-clock read in the kernel and the packages replaced by it, fifty-odd
sites, leaving real only what measures a resource (a pass's compute, a sweep's run, the
process's uptime); the scheduler converting once, where it sleeps, so every timer and every
placed step follows; compose handing pace and epoch to every agent of a world that states a
pace, and the stand-in converting its ticks and waits as it converts its physics. Held to the
code by `tests/test_clock.py`: a tenth of a real second is fourteen of the world's at the
simulation's pace, a deadline of seventy-two of the world's seconds lands in half a real
one, and the simulation fern at 0.47 foresees its crossing four of its own hours out — a
hundred bench seconds — and places the purchase ahead of it, nothing in it knowing the pace.
The bench figure, a stand-in and an agent paced alike over one day of the world, is still to
be taken: it needs the images rebuilt and the society restarted.

# Seams left open

- **The transport's watchdog** measures a quiet bus; on one timeline it measures it in the
  world's seconds, which is right for a world whose devices run on that clock and moot for a
  real one. A world that compresses time and keeps a real board has not been needed.
- **The epoch's origin.** Compose states it when a world is onboarded; whether it should be
  the world's ratification instant is left until two worlds must agree on a date.
- **A test's fast clock** is a convenience this makes possible and nothing here asks for.
