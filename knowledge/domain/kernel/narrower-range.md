---
type: Domain Concept
title: Narrower range
term: http://example.org/orexis#hasNarrowerRange
description: >-
  A range a subject states inside its operating range for one property, narrower by the noise of
  the reading that watches it. Sensing concludes its sides and prediction places its crossings as
  for any range; a desire reads it in the test its wants are reached by.
---

# What it is

```turtle
:bed ssn-system:hasOperatingRange :bed_operating ;
     orexis:hasNarrowerRange :bed_narrower .
:bed_narrower ssn-system:inCondition [ ssn:forProperty climate:SoilMoisture ;
                                       schema:minValue 0.3002 ; schema:maxValue 0.5998 ] .
```

A [region](/domain/sensing/region.md) of a third kind, written as the other two are — a node with a
condition for the property and its two bounds — and stated, like them, by the world. Nothing derives
it from a margin and nothing reads it as one: its bounds are two numbers the world chose, and what
they are for is what the desire reading them says, which is where its wants are
[reached](/domain/planning/reached.md) (#944).

# Why a word of its own, and the kernel's

Stated as a second `ssn-system:hasOperatingRange` it would be read where a subject's operating range
is read for its middle — the dose, the heating and the bid each size an act to it, the sentinel's
firmware sizes its wake window from it and a dashboard paints it — and a met-test reading
`sensing:below` of any range would mint where a reading crosses the narrower floor. So it is attached
by its own property.

That property is the kernel's because two packages meet at it. Sensing's three rules conclude its
sides, and prediction's `ranges_of` places a crossing at each of its bounds, so that a stretch never
straddles one and the side a predicted number is written with holds over the whole stretch; and
prediction speaks no word of sensing's. SSN-System's two kinds are nobody's package either.

# What reads it, and what does not

- **Sensing's rules**, its sides beside the other ranges', a revision of the reading with no memory.
- **Prediction**, its crossings beside the others'.
- **A desire**, by side, in its reaching test — `sensing:below` of any range the subject states is
  below this one too, since this one lies inside the rest.
- **Not the commands.** A dose, a heating and a bid aim at the operating range's middle, and the
  narrower range must hold that middle, or a step sized there lands where its want reads unreached
  and the plan never ends; a world's test holds every shipped narrower range to it
  (`world/greenhouse/tests/test_hysteresis.py`, `world/allotment/tests/test_allotment.py`).

# How wide

The margin is the reading's whole spread: twice what one reading strays either way, which is the most
two readings of one value can differ by. A value resting at the floor then reads below it and never
clears the narrower floor on noise alone, so the want it minted stands until the value has truly
risen; a margin of the one-way figure lets a single extreme draw clear it. The greenhouse states 0.0002
inside the soil's bounds and 0.02 inside the air's — the simulator's count of a ten-thousandth and the
thermometer's `sim:jitter` of a hundredth, each either way — and the allotment the soil's 0.0002. The
terrace states none: it holds no desire, so no test would read the sides of one.
