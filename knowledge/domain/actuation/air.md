---
type: Domain Concept
title: Air
term:
  - http://example.org/orexis/climate#air
  - http://example.org/orexis/climate#Cold
  - http://example.org/orexis/climate#Comfortable
  - http://example.org/orexis/climate#Hot
description: >-
  How a subject's air is believed, in climate's words - cold, comfortable or hot by its temperature
  against the subject's operating range, held past the range's margin - as climate's air transition
  makes it of each air-temperature observation arriving.
---

# What it is

```turtle
:bed climate:air climate:Cold .
```

A subject's **air** says which side of its operating range for `climate:AirTemperature` its
temperature is believed on — `climate:Cold` short of the floor, `climate:Comfortable` between the
bounds, `climate:Hot` past the ceiling. `climate:airRule`, a
[transition](/domain/belief/transition.md) in `domains/climate/rules.ttl`, writes it as a subject
belief when an air temperature is observed; it is the
[soil](/domain/actuation/soil.md)'s rule again over another property, the hold written a second time,
which is the cost the record names of a domain owning its own states.

The greenhouse states a margin of 0.02 on the bed's air, its thermometer's whole spread, so a bed
believed cold at 17.99 is still cold at 18.01 and comfortable from 18.02; one comfortable at 18.00 is
cold at 17.99.

# Who reads it

The greenhouse's desire, which asks that no subject its grower acts for is believed cold, and the
heating, admitted where one is and replacing `climate:Cold` by `climate:Comfortable` (#944).
