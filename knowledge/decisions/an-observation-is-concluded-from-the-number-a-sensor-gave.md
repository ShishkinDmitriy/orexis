---
type: Decision
title: An observation is concluded from the number a sensor gave, by rules over the scaling and calibration the world states
status: accepted
timestamp: 2026-10-01T10:00:00Z
description: >-
  The sovereign's ruling of 2026-09-30/10-01, finishing the terrace's hardware. Sensing stays dumb -
  it keeps the number a sensor gave, who made it and when - and the deliberator concludes by sensing's
  rules what the number is an observation of, its quantity through a two-point scaling (a rescale, the
  unit changing) and its reading through a two-point calibration (a correction, the unit staying),
  each an object the world states beside the sensor; then its sides. The board publishes raw counts.
  Refused - the firmware scaling, a scaling stage of code members, the calibration as the agent's
  belief revised by an act, and received keying an observation by what it is of.
---

# What was true (on main at e752daa4)

The terrace's board converted its probe's ADC count to a fraction with `ADC_DRY`/`ADC_WET`, borrowed
defaults nobody had measured, so wet soil clamped at 1.0 and recalibrating meant retrieving the board
(#26). `received` wrote a whole observation — feature, property, number — keyed by what the sensor
observes of what hosts it, and the pipeline's last stage was a `sensing:Scaling` family of code
members, identity the only one. And the probe was wired to GPIO34, which the FireBeetle 2 ESP32-E
feeds from its battery divider, so every reading was a mix of soil and battery.

# The claim

**The board publishes what it measures and nothing it would have to be told.** The outdoor sentinel
publishes the probe's raw count (`moisture_raw`, from GPIO36 now) and the battery's voltage (`battery`,
off its own divider on GPIO34, the ESP32's factory ADC calibration applied); its ULP watches counts, its
window a quarter of the band's width in counts, sized by the generator from the scaling the world states.

**Sensing keeps the number; the rules say what it is, in layers.** `received` writes one observation per
sensor holding the number the sensor gave (`sensing:rawResult`), who made it and when. Sensing's rules,
run by the deliberator as a revision, conclude at layer 0 the observation's feature of interest and
property from the topology and its quantity (`sensing:scaledResult`) — the number as it is, or through
the [scaling](/domain/sensing/scaling.md) that `sensing:scales` the sensor; at layer 1 its reading —
that quantity as it is, or through the [calibration](/domain/sensing/calibration.md) that
`sensing:corrects` it; at layer 2 its sides. Both lines are unclamped.

**A scaling changes the unit and a calibration does not**, so they are two classes: a probe's count is
rescaled to a moisture, and a thermometer 0.4 off at ice is corrected in degrees. Each is one class with
two points, an object the world states beside the sensor and nothing special: recalibrating is two
numbers edited and the agent restarted, a lived-in volume reading every public graph again at boot.

**Readers of an observation read it with its revisions.** Belief's part hears a graph written before any
package beyond the mind, so the prediction and sensing's own `Observed` find the observation concluded;
both read the graph and its revisions together.

# What was refused

- **The firmware scaling**, what was true: a per-instance, drifting fact in per-model code, and the
  clamp that hid a flooded probe.
- **A scaling stage of code members in the pipeline** — `sensing:TwoPoint`, built and struck the same
  day. Arithmetic over what is stated is a rule; a code member is a second mechanism beside the rules.
  The `sensing:Scaling` family, `scaledBy` and `Identity` went with it.
- **The calibration as the agent's belief, revised by an act** — built and struck the next day: a graph
  kind of the agent's own born from `beliefs/`, a `calibrate` act and an `orexis-calibrate` tool that
  stopped the agent to revise a point. It made a calibration special — its own graph kind, its own
  writer, its own tool, and a boot change so the document stayed the agent's — where it is a fact about
  an instrument like its frequency. Finding the points with a person is #862's plan, which would write
  them as any step's effect writes.
- **`received` keying an observation by what it is of.** What an observation is of is a conclusion from
  the topology; it keys by the sensor now.

# Seams left open

- **A forecast is written whole**: a series sensor's stretches still carry feature, property and value
  from `received`, its values being final units and its stretches not observations of the present.
- **The ULP's window is sized from the scaling when the firmware was generated**; a new measurement moves
  the points but not the board's window until it is regenerated and reflashed.
- **An observation's interval** is remembered by sensing's part from its own start, so the first reading
  after a restart has none.
- **A world's private documents in its committed compose file** — #860.
