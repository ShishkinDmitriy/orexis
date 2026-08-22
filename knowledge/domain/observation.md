---
type: Domain Concept
title: Observation
term: sosa:Observation
description: >-
  The NODE — a `sosa:Observation` recording one act of observing: what was observed, which
  property, the value, when it arrived, and by which procedure. One per (subject, property), and
  it UPSERTS: a new one replaces its predecessor rather than joining it, which is why an effect
  that predicts a value must retract the node it supersedes or leave two results on one node.
  Not the value it carries — that is the reading. It answers two questions no number can: which
  of the two ENDS the figure is (the property's, never the stimulus's), and which INSTANT it is
  stamped with (arrival, always, with room beside it for the device's own).
---

# What it is

An **observation** is the node: a `sosa:Observation` in the sensed graph, recording one act of
observing. It carries the feature of interest, the observed property, the result, the result time
and the procedure used.

It is the record; the [reading](/domain/reading.md) is the value inside it. The distinction earns
its keep in one sentence the project says often — *two readings on one node* — which is the exact
shape of a real defect and is incoherent the other way round, because the node **is** the
observation.

# One per (subject, property), and it replaces

The writer mints a deterministic node from the feature and the property, and writes DELETE then
INSERT. So a new observation **supersedes** its predecessor rather than joining it, and nothing
accumulates.

That upsert is load-bearing beyond tidiness, and the obligation it creates falls on anyone who
predicts a value rather than measures one: an [effect](/domain/effect.md) must retract the node it
supersedes, and that page says what goes wrong when it does not.

Keying it by subject **and** property was itself a correction: keyed by subject alone, a plant's
temperature and its moisture landed on the same node and overwrote each other.

# It says how it was made

`sosa:usedProcedure` carries the sensor's sense mode, which is a `sosa:Procedure`. **That is not
recoverable from the number**, and it changes what a *missing* one means: under
`sensing:ScheduledProcedure` the board is late; under `sensing:PushProcedure` there may simply have
been nothing to say.

It is the clock part of *how*, not the whole method — the codec, the pointer and the scaling are
also how that number came to be.

# Which of the two ENDS the figure is

The figure in an observation is the **property's** — a moisture fraction, a temperature — never
the stimulus's.

What a probe physically responds to is capacitance (`ssn:detects`, entailed from the part), which
*stands in for* moisture (`ssn:isProxyFor`, the part's own statement). The calibration pair is
values **of the stimulus**, and scaling is the crossing between the two ends.

This is why a calibration drifts without anything changing: the proxy relationship degrades — the
capacitance stops standing in for the moisture as well as it did — while neither end moved.

# Which INSTANT it is stamped with

`sosa:resultTime` means **arrival**, always. It is the honest instant an agent with clockless
boards has, and the freshness invariant leans on it.

The day a device speaks for itself — timestamps its own readings, or batches ten and sends one
message — its instant lands in `sosa:phenomenonTime` beside it: *when the result applies to the
world*, as distinct from when we heard. The two coincide for every device here today, and the
writer, the shape and this sentence are ready for the first one where they do not.

# Related

- [reading](/domain/reading.md) — the value this node carries, and what happens to it over time.
- [sensing](/domain/sensing.md) — the capability that produces one, and who holds the clock.
- [an-observation-says-how-it-was-made](/decisions/an-observation-says-how-it-was-made.md).
