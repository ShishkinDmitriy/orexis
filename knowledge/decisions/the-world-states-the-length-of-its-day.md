---
type: Decision
title: The world states the length of its day
status: superseded
superseded-by: the-agent-keeps-one-timeline-and-its-clock-may-run-fast
timestamp: 2026-09-13T21:30:00Z
description: >-
  Found on 2026-09-13 while analysing time: the simulation and the loner worlds run their
  physics one hundred and forty-four times faster than the clock the agent predicts by, and
  the agent does not know it. The stand-ins age by `sim:timeScale`; the agent's drift divides
  real seconds by a literal day. So the fern at 0.47 is foreseen crossing in four hours in a
  world that crosses it in about a hundred seconds, every foresight built that week is dead on
  the bench while its unit tests pass, and the expected next observation's set is far too
  narrow. Ruled: the world states the length of its day as a public fact; a rate per day or per
  hour is in the world's day; a stretch in seconds is the agent's; the stand-ins derive their
  scale from the world's day. Refused — the scale as a substrate knob the mind may not read, and
  rates restated in the agent's clock.
---

> **Superseded the day it was built** by
> [the-agent-keeps-one-timeline-and-its-clock-may-run-fast](/decisions/the-agent-keeps-one-timeline-and-its-clock-may-run-fast.md):
> the finding below stands, the ruling does not. An agent does not know how many seconds
> its hour has; a compressed world is a clock that runs fast, not a fact the rules read.
> The build (#647) was closed unmerged.

# What was found

`world/simulation` and `world/loner` say on their world node that ten bench minutes are one
simulated day, and say why every stand-in must age alike: a dose sized for a day's drying would
otherwise land against an hour's. The simulated sensor integrates drying over real elapsed
seconds times that scale, and so do the daily swing and the meddler. Devices stay real: a valve
pours at its millilitres per real second, a sensor reports at its real cadence.

The agent's drift divides the elapsed seconds it is handed — real, from the pass's landings and
from the expectation's window — by a literal day, and its crossing multiplies by one. The
agent therefore believes the fern at 0.47, drying at 0.12 a day above a floor of 0.45, crosses
in four hours; the simulator crosses it in four simulated hours, about a hundred real seconds.
The loner's sixteen hours are under seven minutes. Every At want derived that week was placed
after the pot had been below its floor for a simulated week, so on the bench only repair after
an observed LOW ever ran; the drift inside imagined worlds barely moved a reading the world
moved by a band; and the expected next observation's bands were far too narrow, so a reviser
waking on surprise would wake on every reading. The terrace is real time and unaffected.
Nothing in the bundle said the agent knows the world's clock, and the code read the term
nowhere.

# What is decided

**The world states the length of its day** — `orexis:secondsPerDay` on the world node, a real
day where the world says nothing. It is not the mind knowing it is simulated, which
[the-substrate-is-not-the-minds](/decisions/the-substrate-is-not-the-minds.md) rightly
forbids: it is the unit the world's rates are stated in. "Per day" means the world's day, and
in those two worlds a day lasts six hundred of the agent's seconds.

**A rate per day or per hour is the world's; a stretch in seconds is the agent's.** Drying,
diffusion and the meddler's mean are stated per world day or hour, and every rule that today
writes a literal day or hour reads the world's instead. Cadence, grace, pour, patience,
foresight and every landing are seconds of the clock the agent and its devices share, and stay
what they are. A crossing computed from a rate therefore comes out in the agent's own seconds,
which is what placing a plan needs.

**The stand-ins derive their scale from the world's day**, one source: `sim:timeScale` becomes
a real day over the world's day, handed to every stand-in by compose as it is now.

**The runbook's crossings are measured on the bench.** A number the rule gives is what the rule
gives; the claim that an agent foresees, places and prevents is a claim about a world, and the
runbook records the world's day beside every crossing from here on.

# What was refused

- **The scale as a substrate knob the mind may not read.** It was listed among the three
  world-scenario knobs when the substrate left the kernel, and that was right of the
  scenario: the mind must not know that a process stands in for a device. The length of a day
  is not the scenario; it is the meaning of a rate, and a mind that models a rate must know
  its unit.
- **Rates restated in the agent's clock.** A world could say the pot dries seventeen times per
  real day and the stand-in could divide; then "day" would mean nothing in the file the
  sovereign writes, and the terrace and the simulation would state the same physics in two
  units.
- **Scaling the agent's own clock.** The bus, the cadence and the valve are real, and an agent
  whose seconds ran at the world's pace would wait a hundred and forty-four times too little
  for a reading.

# What is built

[#646](https://github.com/ShishkinDmitriy/orexis/issues/646): the term, the rules reading it,
compose deriving the scale, the tests and the runbook re-cut to the world's day. First in the
queue, because every measurement after it depends on it.

# Seams left open

- **Foresight in which clock.** Foresight is a stretch in the agent's seconds; a sovereign
  setting it for a compressed world sets it knowing the world's day. Whether it should be
  stated per world day instead is left until a second compressed world asks.
- **A device that ages by the world's day.** A stand-in's pour is real; a real device's is
  too. A world that compresses actuation as well as physics has not been needed.
