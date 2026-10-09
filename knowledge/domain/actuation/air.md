---
type: Domain Concept
title: Air
term:
  - http://example.org/orexis/climate#air
  - http://example.org/orexis/climate#temperature
  - http://example.org/orexis/climate#Cold
  - http://example.org/orexis/climate#Comfortable
  - http://example.org/orexis/climate#Hot
description: >-
  How a subject's air is believed, in climate's words - cold, comfortable or hot by its temperature
  against the subject's operating range, and the temperature in degrees - as sensing makes of the
  latest air-temperature reading. The words `climate:AirTemperature` names for its subject belief.
---

# What it is

```turtle
climate:AirTemperature sensing:valueAs climate:temperature ; sensing:stateAs climate:air ;
    sensing:belowAs climate:Cold ; sensing:insideAs climate:Comfortable ; sensing:aboveAs climate:Hot .

:bed climate:air climate:Cold ; climate:temperature 17.99 .
```

A subject's **air** says which side of its operating range for `climate:AirTemperature` its
temperature is believed on — `climate:Cold` short of the floor, `climate:Comfortable` between the
bounds, `climate:Hot` past the ceiling — and its **temperature** is the thermometer's last reading in
degrees Celsius. Sensing writes them as a [subject belief](/domain/sensing/subject-belief.md) of the
subject; the words are climate's, as the [soil](/domain/actuation/soil.md)'s are.

The greenhouse states a margin of 0.02 on the bed's air, its thermometer's whole spread, so a bed
believed cold at 17.99 is still cold at 18.01 and comfortable from 18.02; one comfortable at 18.00 is
cold at 17.99.

# Who reads it

Nothing yet: the heating still takes the reading and asks its side, and the air is the word it is to
speak.
