# Moisture sentinel

The second firmware, and the inverse temperament of the first (#151). The
[moisture-sensor](../moisture-sensor/) node is **governed**: its agent commands the cadence and
the watch band, and the board keeps them. A sentinel is **autonomous**: `sensing:PushProcedure`,
so it takes no orders at all — no command topic, no subscribe, nothing to parse — and its agent
derives `sensing:Listening` and can only receive.

What it does instead:

- the **ULP watches for MOVEMENT** — the last published value plus or minus `WAKE_DELTA` — and
  the world's operating range is not watched at all. It used to be, and the promise that made
  ("a board that takes no orders can still keep a promise the world wrote") was the sharpest
  thing about this design; it cost an alarm every patrol, forever, whenever a pot sat outside
  its range, which is exactly when the society least needs a board shouting. The range still
  SIZES the trigger, since `WAKE_DELTA` is `sensing:alarmDeltaFraction` of its width. See
  [the-sentinel-alarms-on-movement](../../knowledge/decisions/the-sentinel-alarms-on-movement.md);
- an **alarm wakes the radio** and publishes `{"moisture":…,"wake":"alarm"}` — something
  happened, so the world hears it, rather than waiting out the rest of the heartbeat;
- a slow **heartbeat** publishes regardless (`HEARTBEAT_S`, generated to fit under the polling
  agent's `sensing:maxReadingAgeS`), so silence stays distinguishable from death.

The watch runs at **two rates**, because patrolling and confirming are different jobs: a slow
`WATCH_PATROL_S` asks "has anything changed", a fast `WATCH_CONFIRM_S` decides whether a
suspicious look was real, and the ULP picks between them from the path it takes through its own
program. The patrol interval is the detection **latency** — at 60 s the value can travel further
than a band width between looks, so this catches where a pot ENDED UP within a minute rather
than the act of watering. The original one-second derivation from the worst credible slew is
still in [`src/ulp_watch.cpp`](src/ulp_watch.cpp) and still explains what a fast patrol buys.

**The ADC has two owners.** Arduino's `analogRead()` holds ADC1 and the coprocessor cannot have
it at the same time, so `setup()` stops the ULP before reading and hands the unit over
explicitly before sleeping. Getting that wrong is silent — the ULP reads full scale forever —
and it needs ESP-IDF 5.x, which is why this project pins its own platform in
[`platformio.ini`](platformio.ini). See
[two-owners-of-one-peripheral](../../knowledge/decisions/two-owners-of-one-peripheral.md).

Declare a board with `mc:firmware "moisture-sentinel"`, mark its channel
`ssn:implements sensing:AlarmProcedure`, run `orexis-firmware <world>`, and flash. **No world
declares one yet**, so `render_sentinel` has never run for a real board and the bench config was
written by hand:

```bash
pio run -t upload      # from this directory
pio device monitor
```

## Which firmware for battery?

Estimated from this bench's own numbers: a full radio wake (boot, WiFi, publish, release) is
~8–9 s at ~100 mA ≈ **0.25 mAh**; the ULP vigil is ~150 µA ≈ **3.6 mAh/day**. One wake buys
about a hundred minutes of watching — speaking is the cost, watching is noise.

| configuration | wakes/day | ≈ mAh/day | 2000 mAh cell |
|---|---|---|---|
| governed @ slow 600 s + watch | 144 | 40 | ~7 weeks |
| governed, realistic (bursts, verification) | 180–240 | 50–65 | ~5 weeks |
| sentinel, heartbeat 600 s | ~146 | 40 | ~7 weeks |
| **sentinel, heartbeat 1 h** | ~26 | **10** | **~6 months** |
| sentinel, heartbeat 4 h | ~8 | 6 | ~11 months |

**The battery is spent by the agent's epistemology, not by the firmware.** The sentinel's
heartbeat is generated under the polling agent's `sensing:maxReadingAgeS`, so the same board is
either no better than the governed node or four times better depending on that one belief. The
crossing promise is what makes a generous one safe: silence means *nothing crossed*, freshness
work moves off the heartbeat onto the ULP, and the heartbeat only proves liveness. A world that
deploys a sentinel and keeps a twelve-minute freshness rule has bought the watcher and declined
the savings. Past ~4 h the vigil itself dominates (~3.6 of 6 mAh), which is where the
energy-budget seam's real question — pricing the watching — begins.
