---
type: Decision
title: The alarm answers to the last report
description: The deviation limit measures from the last value that LEFT the board, re-anchored
  only by a successful publish — so slow drift is the cadence's story, the between-reports jolt
  is the alarm's, and the band edge catches what creeps. Which watcher pays for vigilance is
  decided by the same evidence, the opposite way round.
status: superseded-in-part
superseded-by: the-sentinel-alarms-on-movement
timestamp: 2026-08-15T21:19:41Z
---

> **Superseded in part** by
> [the-sentinel-alarms-on-movement](/decisions/the-sentinel-alarms-on-movement.md). The anchor
> argument below still holds everywhere and is the substrate for both firmwares: the deviation
> limit measures from the last value that LEFT the board. What does not hold is the third
> bullet — "the band catches what creeps" — for the SENTINEL, which no longer watches the
> operating range at all. On the bench the band half alarmed hardest exactly when it had least
> to say: a pot outside its range breached every look, so the board woke the radio every patrol
> forever, and the intersection with the deviation window went empty. The governed node, whose
> band arrives from an agent that can retract it, is unaffected and still watches both.

# The alarm answers to the last report

The deviation half of the alarm (#151) needs an anchor: moved more than delta *since when*?
Three candidates existed, and the code chose before this record said why. The ULP's previous
sample (a second ago), the last *reported* value (whenever a publish last succeeded), or the
last alarm (whenever the news last broke). The answer is the middle one, and it is the same in
all three implementations: the governed firmware's `noteReported()` runs only after
`mqtt.publish` returns true, the sentinel does the same, and the simulator's `last_reported`
moves only when a report goes out. Between publishes the anchor holds still, and the per-second
looks die in a register — sampling is not reporting, and an anchor that trailed the samples
would make the limit a slew detector that only ever compared a value to itself a second ago.

## The question that tests the choice

"Does a slowly changing signal never alarm, then?" — asked of the bench, and worth recording
because the answer is the design. A signal drifting at delta-per-hour walks away from a held
anchor sample by sample, and the moment the cumulative excursion exceeds delta the window
breaks. Drift is never *invisible* to the deviation limit. But the board also reports on its
ordinary clock — the commanded cadence, or the sentinel's heartbeat — and **every such report
re-anchors**. So drift slower than delta-per-reporting-interval never fires the deviation
alarm, and that is not a hole but the division of labour:

- **the cadence carries the slow story** — each scheduled report conveys the drifted value and
  resets the window, so gradual change arrives as ordinary readings;
- **the deviation limit catches the between-reports event** — the watering can, the knocked
  pot, the leak still in-range: what moves faster than the cadence can see;
- **the band catches what creeps** — HI/LO is fixed in world terms and never re-anchors, so a
  month-long dry-down still alarms at the edge however gently it got there.

The picture an agent holds is therefore never staler than min(cadence, time for the signal to
move delta), and — on the governed node — never blind past the band. A sentinel is: it watches
movement alone, and a creep that never exceeds delta between reports reaches its agent as
ordinary readings rather than as an alarm.

One property fell out for free: a failed publish skips `noteReported`, the anchor stays stale,
and the next look very probably alarms again — a crude retry that costs no code and no state.

## Who pays for vigilance is re-picked, not fixed

The fraction itself is the agent's own revisable belief
(`sensing:alarmDeltaFraction` — see
[a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md)), and the
rule that re-picks it reads the cadence review's own evidence the opposite way round, because
**the two watchers trade the vigil**: a lively world earns a tight cadence and a coarse delta —
the readings already carry the news, and alarm wakes on routine liveliness buy nothing — while
a still world earns a slow cadence and a fine delta, because the ULP is then the only watcher
left and a fine threshold on a still value costs nothing at all. Either way the battery is
spent where the information is, which is the alarm's whole economics: a radio wake is
~0.25 mAh, the ULP vigil ~150 µA, and the agent's epistemology — not the firmware — decides
how often each is paid.

## The spike question, decided (#180)

A single-sample spike used to wake the radio: the ULP woke on the FIRST out-of-window look, so
one ADC glitch bought a full ~0.25 mAh publish of a normal-looking value. Three mechanisms were
weighed and priced — a **persistence counter in the ULP** (~0.0001 mAh, N−1 seconds of latency
inside the overshoot allowance the 1 s period was derived from); a **main-core confirmation
without radio** (≈0.004 mAh per suspect wake, but it needs hysteresis or a value on the edge
chatters, and suppressing the publish hides from the review exactly the evidence it feeds on);
and **publish-anyway**, the costliest and the most honest. The sovereign chose without waiting
for the recorded trigger, and chose the counter — `sensing:alarmPersistenceLooks 2`,
constitutional beside `steadyFraction` because what counts as evidence of a real event is the
society's to say, compiled into both firmwares' ULP programs and mirrored by the stand-in's
watch loop so the bench rehearses the boards. The argument is the watch period's own, extended:
a breach visible in exactly one look is not physics. The layering that falls out is the
division of labour again, one level down — **the ULP filters what isn't physics, the main core
upgrades the testimony (its 16-sample average, never the ULP's raw count), and the agent judges
what it means**; a wake whose fresh average reads back in-window still publishes, marked
`"wake":"alarm"`, because the publish is what re-anchors the deviation window (suppressing
would chatter through the stale anchor) and a jolt that settled is still news the delta review
feeds on. Nothing above the ULP ever discards an event.

# Seams left open
- **No second anchor for drift-since-the-last-alarm.** "Wake me when it has moved delta since
  the news last broke, even though ordinary reports re-anchored it" would need an anchor only
  alarm wakes reset. No scenario on this bench wants it; the cadence already carries what it
  would report.
