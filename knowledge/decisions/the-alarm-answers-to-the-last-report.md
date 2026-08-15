---
type: Decision
title: The alarm answers to the last report
description: The deviation limit measures from the last value that LEFT the board, re-anchored
  only by a successful publish — so slow drift is the cadence's story, the between-reports jolt
  is the alarm's, and the band edge catches what creeps. Which watcher pays for vigilance is
  decided by the same evidence, the opposite way round.
---

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
move delta), and never blind past the band.

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

# Seams left open

- **A single-sample spike wakes the radio.** The ULP wakes on the FIRST out-of-window look, so
  one ADC glitch buys a full ~0.25 mAh publish of a normal-looking value. Three mechanisms
  exist, priced: a **persistence counter in the ULP** (require N consecutive breaching looks
  before `I_WAKE`; ~0.0001 mAh and N−1 seconds of latency, well inside the overshoot allowance
  the 1 s watch period was derived from); a **main-core confirmation without radio** (wake,
  take the ordinary 16-sample average, compare it to the window already sitting in RTC memory,
  and sleep again if it holds — ≈0.004 mAh for a 200–400 ms boot that never touches WiFi,
  sixty times a ULP look and sixty times cheaper than the publish, but it needs hysteresis or
  a value sitting exactly on the edge chatters); or **today's publish-anyway**, which costs the
  most and is the only one that lets the agent SEE the noise — and spurious alarm wakes are
  exactly the evidence the delta review feeds on. Undecided, and deliberately: nothing on the
  bench has yet shown an alarm wake whose published value sat inside the window. That
  observation is the trigger for choosing. If N ever becomes configurable it is likelier a
  constitutional figure beside `sensing:steadyFraction` — what counts as evidence is the
  society's to say — than a per-agent pick riding the alarm command, though the command has
  room for it.
- **No second anchor for drift-since-the-last-alarm.** "Wake me when it has moved delta since
  the news last broke, even though ordinary reports re-anchored it" would need an anchor only
  alarm wakes reset. No scenario on this bench wants it; the cadence already carries what it
  would report.
