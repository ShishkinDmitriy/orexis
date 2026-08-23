# Moisture sentinel

The second firmware, and the inverse temperament of the first (#151). The
[moisture-sensor](../moisture-sensor/) node is **governed**: its agent commands the cadence and
the watch band, and the board keeps them. A sentinel is **autonomous**: `sensing:PushProcedure`,
so it takes no orders at all — no command topic, no subscribe, nothing to parse — and its agent
derives `sensing:Listening` and can only receive.

What it does instead:

- the **ULP watches a band compiled in at flash time** from the world's own operating range for
  the pot it sits in (`WAKE_BAND_LOW`/`HIGH` in the generated `config.h`) — a board that takes
  no orders can still keep a promise the world wrote;
- a **alarm wakes the radio** and publishes `{"value":…,"wake":"alarm"}` — the world
  changed, so the world says so, within about a second;
- a slow **heartbeat** publishes regardless (`HEARTBEAT_S`, generated to fit under the polling
  agent's `sensing:maxReadingAgeS`), so silence stays distinguishable from death.

The internal one-second watch cadence is *derived, not guessed* — see the worst-credible-slew
derivation in [`src/ulp_watch.cpp`](src/ulp_watch.cpp): for soil moisture the fastest credible
move is water arriving at percolation speed, a crossing persists once it happens, and the
period therefore bounds detection **latency**, never detection probability.

Declare a board with `mc:firmware "moisture-sentinel"`, mark its channel
`ssn:implements sensing:AlarmProcedure`, run `orexis-firmware <world>`, and flash:

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
