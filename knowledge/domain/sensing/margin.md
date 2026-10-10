---
type: Domain Concept
title: Margin
term: http://example.org/orexis/sensing#margin
description: >-
  How far past a bound of an operating range a value must go to leave the state the agent holds of
  its subject - one number on the range's condition, beside the bounds it widens, sized from the
  instrument's noise. Read by a domain's transition beside the state it replaces; a value coming
  from another state crosses at the bound itself. The sides ignore it.
---

# What it is

```turtle
:bed_operating ssn-system:inCondition [ ssn:forProperty climate:SoilMoisture ;
    schema:minValue 0.30 ; schema:maxValue 0.60 ; sensing:margin 0.0002 ] .
```

A **margin** is hysteresis in value against an instrument's noise. A bed believed dry stays dry
until its soil reads the floor and the margin, 0.3002 here; one believed wet stays wet until its
soil falls to the ceiling less the margin; and a value coming from any other state crosses at the
bound itself, so a real drop out of the range is believed at once. Readings of 0.2990, 0.3001,
0.3001 and 0.3001 are dry four times, and 0.3002 is moist. With no margin stated it is nought, and
the state is the bare comparison of the reading with the bounds; so is the first reading of a key,
which has no [subject belief](/domain/belief/subject-belief.md) before it to hold anything.

SSN-System's conditions have no word for it, so the word is sensing's: sensing speaks SOSA and SSN
and declares what they lack. What it is read for is a domain's: climate's
[transitions](/domain/belief/transition.md), one for the soil and one for the air, each coalescing an
absent margin to nought.

# Where the memory is

Nowhere but the subject belief. A Schmitt trigger's state is its output and not its last input, and
the state judged before is the state judged before that, all the way back; the subject belief is
that state, and a transition reads it as a premise and replaces it. No side is carried onto an
observation and no rule remembers anything the store does not hold
([an-observation-is-a-percept-and-the-mind-reads-only-beliefs](/decisions/an-observation-is-a-percept-and-the-mind-reads-only-beliefs.md)).

It is read on the operating range alone. The sides a [region](/domain/sensing/region.md) is
concluded with do not read it, and no transition judges a survival range, so a margin stated there
is read by nothing.

# How big

The instrument's whole spread, twice what a reading strays either way. A value resting exactly at
the floor is read anywhere within the noise on both sides of it, so a margin of the one-way figure is
cleared by one extreme draw of a value that never moved; the whole spread is cleared only once the
value itself has left the floor's noise. The greenhouse's probe strays a count of the four places it
is published to and its thermometer a hundredth of a degree, so its soil states 0.0002 and its air
0.02; the allotment's plots state 0.0002 for the same probe.

`orexis-onboard` refuses three (`onboarding/reading.py`, `unholdable`): one that is no number, with
which a transition's sum binds nothing, so a subject held in a state would be judged in none; a
negative one, which widens nothing, so a transition would read as nought a figure the world stated;
one of half its range's width or more, since every act here aims at the middle of a range and a
subject a step brought there would still be believed in the state it came from. A range with no name
is judged like any other, and said as one with no name where its margin is refused.
