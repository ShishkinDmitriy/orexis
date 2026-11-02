---
type: Domain Concept
title: Defect
term: http://example.org/orexis/sensing#defect
description: >-
  Why a sensor's numbers are not what it says it observes, stated by the world of the sensor, since no
  rule can tell a fresh and varying number from a true one. Its percepts are kept and carry why; sensing
  concludes no reading of them, so nothing believes them; the series still draws them, tagged. The third
  doubt about a reading, and the one stated rather than concluded.
---

# What it is

```turtle
# world/terrace/world.ttl
:battery_sensor_terrace sensing:defect
    "its channel reads the soil probe's charge, not the cell: the divider has no capacitor for the ADC to sample (#939)" .
```

A sensor is **defective** when what it reports is not what it observes: a
channel that measures another's charge, a probe wired to the wrong pin. The world says so of the sensor,
in its own document, as testimony about the device, and the value says why. Nothing detects it: a
silent sensor ([observer](/domain/sensing/observer.md)) is late and a [stuck](/domain/sensing/stuck.md) one repeats
itself, and a defective one may do neither - the terrace's battery channel gave a fresh, varying, plausible
voltage for weeks, and it was the probe's count.

# What sensing does with it

- **Its [percepts](/domain/sensing/observation.md) are kept**, with the number the sensor gave and its
  quantity, and each carries the defect, concluded in its revision by sensing's rule.
- **No reading is concluded of them**: both reading rules pass over a defective sensor, so nothing that reads
  a reading - a domain's transition, a command sizing a step, a drift - believes one.
- **The series still draws it**: its point carries the quantity it gave, tagged `defective`, so what the world
  doubts is watched, and the day it is mended shows.
- **A person is told**: sensing's askable answers the defect and the number beside the latest percept, and
  sensing's account line names it.

Mending it is taking the statement out of the world.
