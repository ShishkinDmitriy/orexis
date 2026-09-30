---
type: Decision
title: An observation is concluded from the number a sensor gave, by rules over a calibration the agent believes
status: accepted
timestamp: 2026-09-30T16:00:00Z
description: >-
  The sovereign's ruling of 2026-09-30, finishing the terrace's hardware. Sensing stays dumb - it
  keeps the number a sensor gave, who made it and when - and the deliberator concludes, by sensing's
  rules, what that number is an observation of and what quantity it is, from the topology and a
  calibration the agent believes of the sensor and revises when told what it reads now. The board
  publishes raw counts. Refused - the firmware scaling, a scaling stage of code members in the
  pipeline, the calibration as a fact of the world, and received keying an observation by what it is of.
---

# What was true (on main at e752daa4)

The terrace's board converted its probe's ADC count to a fraction with `ADC_DRY`/`ADC_WET`, borrowed
defaults nobody had measured, so wet soil clamped at 1.0 and recalibrating meant retrieving the
board (#26). `received` wrote a whole observation — feature, property, number — keyed by what the
sensor observes of what hosts it, and the pipeline's last stage was a `sensing:Scaling` family of code
members, identity the only one. And the probe was wired to GPIO34, which the FireBeetle 2 ESP32-E
feeds from its battery divider, so every reading was a mix of soil and battery.

# The claim

**The board publishes what it measures and nothing it would have to be told.** The outdoor sentinel
publishes the probe's raw count (`moisture_raw`, from GPIO36 now) and the battery's voltage (`battery`,
off its own divider on GPIO34, the ESP32's factory ADC calibration applied); its ULP watches counts,
its window a quarter of the band's width in counts, sized by the generator from the calibration the
agent is born believing.

**Sensing keeps the number; the rules say what it is.** `received` writes one observation per sensor
holding the number the sensor gave (`sensing:rawResult`), who made it and when. Sensing's rules,
run by the deliberator as a revision, conclude at layer 0 the observation's feature of interest (what
the sensor is hosted by, a sample or the subject), its property (what the sensor observes) and its
reading — the number as it is, or on the straight line through the two
[calibration](/domain/sensing/calibration.md) points the agent believes, unclamped — and at layer 1 its
sides. A thermometer's degrees are already a quantity and pass as they are; a probe's count is made a
moisture.

**The calibration is the agent's belief**, a `sensing:CalibrationGraph` of its own, born from
`beliefs/<agent>.ttl` and revised by `calibrate` — told "the probe is in dry air now", the point takes
the latest number — which `orexis-calibrate` runs for a running agent, in its own image, while it is
stopped. It is public knowledge the agent owns, since a reading is revised beside public knowledge.

**Readers of an observation read it with its revisions.** Belief's part hears a graph written before
any package beyond the mind, so the prediction and sensing's own `Observed` find the observation
concluded; both read the graph and its revisions together.

# What was refused

- **The firmware scaling**, what was true: a per-instance, drifting fact in per-model code, and the
  clamp that hid a flooded probe.
- **A scaling stage of code members in the pipeline** — `sensing:TwoPoint`, built and struck the same
  day. Arithmetic over beliefs is a rule, revised when the belief is; a code member is a second
  mechanism beside the rules, and every reader of the quantity would have had to trust the pipeline
  had run. The `sensing:Scaling` family, `scaledBy` and `Identity` went with it.
- **The calibration as a world fact**, recommended and not chosen: public in the world's document it
  would be edited and restarted, but it is one agent's understanding of one probe, which that agent
  revises and keeps — #26's reading, and the sovereign's.
- **`received` keying an observation by what it is of.** What an observation is of is a conclusion from
  the topology, and received knowing it was received deciding it; it keys by the sensor now.

# Seams left open

- **A forecast is written whole**: a series sensor's stretches still carry feature, property and value
  from `received`, its values being final units and its stretches not observations of the present.
- **The ULP's window is sized from the calibration the agent is born believing**; a recalibration told
  later moves the points but not the board's window until it is regenerated and reflashed.
- **An observation's interval** is remembered by sensing's part from its own start, so the first
  reading after a restart has none.
- **A world's private documents in its committed compose file** — #860.
