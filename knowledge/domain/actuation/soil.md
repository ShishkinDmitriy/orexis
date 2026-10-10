---
type: Domain Concept
title: Soil
term:
  - http://example.org/orexis/climate#soil
  - http://example.org/orexis/climate#Dry
  - http://example.org/orexis/climate#Moist
  - http://example.org/orexis/climate#Wet
description: >-
  How a subject's soil is believed, in climate's words - dry, moist or wet by its moisture against
  the subject's operating range - as sensing makes of the latest soil-moisture reading.
  The words `climate:SoilMoisture` names for its subject belief.
---

# What it is

```turtle
climate:SoilMoisture sensing:stateAs climate:soil ;
    sensing:belowAs climate:Dry ; sensing:insideAs climate:Moist ; sensing:aboveAs climate:Wet .

:bed climate:soil climate:Dry .
```

The **soil** of a subject is the state it is believed in for `climate:SoilMoisture`: `climate:Dry`
under the floor of the subject's operating range for it, `climate:Moist` within, `climate:Wet` over
the ceiling. It is a [subject belief](/domain/sensing/subject-belief.md), one per subject,
which sensing writes; climate owns the words and nothing else of it, and the judgment — the bounds,
the [margin](/domain/sensing/margin.md) and the state before — is sensing's rule.

A bed believed dry at 0.2990 stays dry at 0.3001 with the greenhouse's margin of 0.0002, and is moist
at 0.3002; a moist bed reading 0.2999 is dry at once.

# Who reads it

No desire and no action yet: the [dose](/domain/actuation/actuation.md) and the growers' desires
still read the reading and its side. The soil is the word they are to speak.
