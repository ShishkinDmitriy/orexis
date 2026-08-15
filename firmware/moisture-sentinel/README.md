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
- a **crossing wakes the radio** and publishes `{"value":…,"wake":"crossing"}` — the world
  changed, so the world says so, within about a second;
- a slow **heartbeat** publishes regardless (`HEARTBEAT_S`, generated to fit under the polling
  agent's `sensing:maxReadingAgeS`), so silence stays distinguishable from death.

The internal one-second watch cadence is *derived, not guessed* — see the worst-credible-slew
derivation in [`src/ulp_watch.cpp`](src/ulp_watch.cpp): for soil moisture the fastest credible
move is water arriving at percolation speed, a crossing persists once it happens, and the
period therefore bounds detection **latency**, never detection probability.

Declare a board with `mc:firmware "moisture-sentinel"`, mark its channel
`ssn:implements sensing:CrossingProcedure`, run `agora-firmware <world>`, and flash:

```bash
pio run -t upload      # from this directory
pio device monitor
```
