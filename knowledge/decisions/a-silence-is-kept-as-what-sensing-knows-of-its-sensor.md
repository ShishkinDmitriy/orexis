---
type: Decision
title: A silence is kept as what sensing knows of its sensor
status: accepted
timestamp: 2026-11-04T12:00:00Z
description: >-
  The sovereign's ruling of 2026-11-04 that sensing collects what it knows of its sensors, so a sensor that
  sends nothing leaves a record. Decided - the first ask that finds a sensor silent keeps a
  sensing:SilenceGraph saying since when, its next reading says until when and ends it, and it is kept for
  good, handed to no reader of the mind. Refused - leaving a silence computed alone, a silence the mind
  believes, and a journal event as its only record.
---

# The question

Asked which sensors the terrace has, the model answered with readings nineteen days old as the latest. The
agent knew better: sensing had said each sensor silent in the log at boot. But the store held no word of it,
since [a silence was computed and never written](/domain/sensing/sensing.md), and a reader of the store could
find it only by doing `missed`'s arithmetic itself. The sovereign: *sensing should collect knowledge about its
sensors. If it sends nothing, we should have a record of it.*

# What was decided

**The first ask that finds a sensor silent keeps the silence.** Sensing's part writes one
`sensing:SilenceGraph`, the agent's own, saying `<sensor> sensing:silentSince` the instant its latest reading
stopped being the present, its period starting there. A silence already holding is not written again, so a
restart says it neither in the store nor in the log.

**A reading ends it, and it is kept.** `received` says `silentUntil` the reading's instant and ends the
graph's period there. Nothing forgets it, so the sensor's outages stay after the percepts around them have
been forgotten, kept only as deep as the stuck rule reads. This is what [stuck](/domain/sensing/stuck.md) and
[defect](/domain/sensing/defect.md) already were, triples about the sensor; silent was the one doubt about a
sensor that no reader could find.

**No reader of the mind is handed one.** The kind is beneath `orexis:Graph` alone, as an observation's is. What
the mind holds of a silent sensor is still that the belief made of its last reading has ended.

# What was refused

**Leaving a silence computed alone.** The argument for it was that a stored silence is a second record of what
the latest percept's period says, and that nothing in the mind reads one. The first premise holds only while
the silence lasts: once a reading arrives and the percepts are forgotten, no period says the sensor was ever
silent, so the record is the only one there is. The second premise is still true and decides the kind, not
whether the silence is kept. The old silence graph was also deleted when a reading arrived, which is why the
next reading had to find it. This one is ended and kept.

**A silence the mind believes.** A `orexis:BeliefGraph` would be forked into every possible world and read by
revision. No plan branches on it, since the ended belief already makes the mind hold nothing current of the
subject ([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).

**A journal event as its only record.** The [journal](/decisions/the-journal-is-the-agents-flight-recorder.md)
keeps what happened for good, and a `FellSilent` event there would have been read by the model's `journal`
tool. But the journal records what the agent did, and a silence is what sensing knows of a sensor, beside its
defect and whether it is stuck. A chat that reads the store and not the journal would still not see it, and
neither would any reader of the store.

# Seams left open

- **A sensor that has never reported is not silent.** Its absence looks like a sensor not yet due, as before.
- **Nothing sweeps old silences.** One graph per outage is small, and none has yet needed forgetting.
