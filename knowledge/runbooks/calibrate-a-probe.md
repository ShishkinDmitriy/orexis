---
type: Runbook
title: Calibrate a probe
description: >-
  Rewire a board's probe off its battery pin, flash the firmware that publishes raw counts, and tell
  the agent what the probe reads in dry air and in water - no reflash to recalibrate again.
---

# Once: the board

The terrace's FireBeetle 2 ESP32-E feeds its battery's voltage onto GPIO34 (A2) through its own
divider, so the probe's signal lead moves to **A0 (GPIO36)**; power and ground stay on 3V3 and GND.
The battery is a 1S LiPo on the JST port — check the plug's polarity first — and USB is not
plugged in while anything but a lithium cell is on that port.

```bash
orexis-firmware terrace                                  # config.h: MOISTURE_PIN 36, BATTERY_PIN 34
cd firmware/outdoor-sentinel && pio run -t upload        # board on /dev/ttyUSB0, no monitor holding it
```

A power-cycle makes the board publish at once. The agent's log then shows five readings — the soil,
the air's three and `battery_sensor_terrace` in volts.

# Whenever: the calibration

The probe's dry and wet counts are the agent's belief (`world/terrace/beliefs/terrace.ttl` is only
what a newborn agent believes). Hold the probe in dry air, power-cycle the board so it publishes,
then tell the agent:

```bash
orexis-calibrate terrace terrace moisture_sensor_terrace dry
```

Then the probe in a glass of water, up to its line, power-cycle, and:

```bash
orexis-calibrate terrace terrace moisture_sensor_terrace wet
```

Each stops the agent, revises the point in its own volume from the latest raw count, and starts it
again; `--raw N` takes a count you read yourself instead. The next reading is concluded through the
new points. Put the probe back in the bed: its moisture now reads between nought and one, past them
where the soil is drier than the air or wetter than the glass.

If the band the ULP watches matters — it was sized from the birth calibration — regenerate and reflash
after a large change: `orexis-firmware terrace` reads `beliefs/terrace.ttl`, so copy the numbers there
first.
