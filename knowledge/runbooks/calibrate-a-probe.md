---
type: Runbook
title: Calibrate a probe
description: >-
  Rewire a board's probe off its battery pin, flash the firmware that publishes raw counts, read the
  count in dry air and in water off the agent's log, and write them into the world's scaling.
---

# Once: the board

The terrace's FireBeetle 2 ESP32-E feeds its battery's voltage onto GPIO34 (A2) through its own
divider, so the probe's signal lead moves to **A0 (GPIO36)**; power and ground stay on 3V3 and GND.
The battery is a 1S LiPo on the JST port — check the plug's polarity first — and USB is not plugged in
while anything but a lithium cell is on that port.

```bash
orexis-firmware terrace                                  # config.h: MOISTURE_PIN 36, BATTERY_PIN 34
cd firmware/outdoor-sentinel && pio run -t upload        # board on /dev/ttyUSB0, no monitor holding it
```

A power-cycle makes the board publish at once. The agent's log then shows five readings — the soil's
count, the air's three and `battery_sensor_terrace` in volts.

# Whenever: the scaling

What the probe's count means is the world's [scaling](/domain/sensing/scaling.md), `:probe_scaling` in
`world/terrace/world.ttl`. Hold the probe in dry air, power-cycle the board, and read what it gave:

```bash
podman logs --since 2m orexis-terrace_agent-terrace_1 | grep "moisture_sensor_terrace reads"
```

Then the probe in a glass of water up to its line, power-cycle, and read it again. Put the two counts in
the scaling's `dry` and `wet` points and restart the agent — a lived-in volume reads the world again at
boot, and the next reading is rescaled through them:

```bash
podman restart orexis-terrace_agent-terrace_1
```

The board's wake window was sized from the scaling when its firmware was generated; after a large change,
`orexis-firmware terrace` and reflash so it watches the right width.
