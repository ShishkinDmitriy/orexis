---
type: Decision
title: A panel is a sensor, not an agent, and it draws what the world says
description: One panel per agent put every property that agent records on one axis under one unit, so a 23.9 degree reading was drawn as 2390% and thresholds meant for soil moisture coloured a temperature. A panel is keyed on the sensor now — one row each, history beside current value — because a sensor observes one property, states one unit, and its subject states the range that property belongs in. Nothing about units or bands is written in the generator; all three come from the world.
status: accepted
stage: v1
tags: [grafana, onboarding, units, ssn, observability]
timestamp: 2026-08-12T00:00:00Z
---

# What was wrong

Three defects, one cause.

```python
"unit": "percentunit",                      # every panel
"min": 0, "max": 1,                         # every panel
"thresholds": [red, orange@0.25, green@0.4] # every panel
```

A panel was keyed on the **agent**, and an agent's bucket holds every property it records. So one
axis carried a soil moisture, an air humidity and an air temperature; the unit was a guess that
happened to suit two of them; and **23.9 °C was drawn as 2390%**. The thresholds were a
soil-moisture opinion applied to temperature.

The generator's own `_flux` had noticed half of this — it grouped by the `property` tag
specifically so a temperature would not be *plotted as* a moisture — and then put the series it
had carefully separated onto one axis with one unit.

# A panel is a sensor

One **row per sensor**: history at 16 columns, current value at 8. Rows are the number of sensors.

A sensor is the right key because it is the thing that has the facts a panel needs:
`sosa:observes` one property, `scaling:quantityUnit` one unit, and `perception:monitors` a subject
whose ranges say what the property should sit in. An agent has none of those — it has a bucket.

**Units come from the world.** `unit:DEG_C` → `celsius`, `unit:UNITLESS` → `percentunit`,
`unit:PERCENT`, `unit:LUX`. An unknown unit renders as `none` rather than a guess, because
guessing is how the temperature came to be a percentage. That `UNITLESS` maps to a percentage is a
fact about **this project** and not about the unit — soil moisture is a fraction of saturation and
relative humidity a fraction of one, both stored 0-1 — and a unitless quantity that was not a
fraction would need saying here.

# Colour comes from what the subject can stand

Both ranges earn their place, ascending the way Grafana reads them:

| | |
|---|---|
| below survival | **red** |
| survival to operating | **orange** — alive but not well, the state worth seeing before it is red |
| inside operating | **green** |
| above operating, above survival | orange, then red |

A subject stating only one range gets the degraded form; one stating none gets a single neutral
step and the panel holds no opinion. **That is the honest fallback** — the old hardcoded 0.25/0.4
was an opinion about moisture asserted over every property.

The axis is bounded by the survival range where one is stated, widened a tenth so a value at the
limit is drawn rather than clipped. Pinning every panel to 0-1 is what hid a temperature.

# A sensor must now say what unit it reads in

`scaling:AUnitIsAUnitShape` was `maxCount 1` on `sh:targetSubjectsOf scaling:quantityUnit` — which
can only check the sensors that already comply. Its comment recorded the gap and its reason: only
one world stated units, and requiring them would have refused the others.

The gap has been paid for since, so the reason is gone. Both worlds state units — two in
`simulation` were backfilled here — and the shape targets `sosa:Sensor` with `minCount 1`. A
sensor without a unit is a reading nothing downstream can draw.

# Seams left open

- **`world/sensing` states no range at all**, so its panels are correctly colourless. Its subject
  is a bare `sosa:FeatureOfInterest`, and typing it `water:Plant` would require a
  `water:servedBy` the bench does not have. Ranges hang off any subject — `ssn-system:` declares
  no domain — so stating them there needs no plumbing, only a decision about what that pot is.
- **The agent's own desired range is not drawn**, because there is no such term. `water:hasTarget`
  is a point, and `water:bandLow`/`bandHigh` are a band the market's bidder holds — soil-moisture
  only, and absent from an agent that merely records. A range an agent picks *within* the
  subject's, per property, is the missing thing; see [#110](https://github.com/ShishkinDmitriy/agora/issues/110).
- **Health dashboards were not touched.** They are per agent, which is correct — a bucket going
  quiet is an agent's property, not a sensor's.
