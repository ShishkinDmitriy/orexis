# Outdoor sentinel

**The sentinel for an outdoor node**: [moisture-sentinel](../moisture-sentinel/) copied onto a
**DFRobot FireBeetle 2 ESP32-E** with a **BME280** beside the soil probe and the board's own
WS2812 as the status lamp. `world/terrace` deploys it. Everything that makes a sentinel a
sentinel is unchanged — `sensing:PushProcedure`, no command topic, the ULP's movement watch at
`WATCH_PATROL_S`/`WATCH_CONFIRM_S`, `WAKE_DELTA` sized from the subject's operating range, the
heartbeat generated under the polling agent's `sensing:maxReadingAgeS`, the wifi and MQTT
handling and retry budget. Its agent derives `sensing:Listening`.

**This is a copy, and the copy is the cost.** `src/ulp_watch.cpp` and `include/ulp_watch.h`
are byte-for-byte the sentinel's, kept in step by hand; `src/main.cpp` is the sentinel's with
the BME280 and WS2812 blocks added; `ontology.ttl` restates the sentinel's three promises under
a namespace of its own, because a world's device is typed with one firmware class. A fix to
the ULP program in one directory does not reach the other, and nothing checks they agree. The
author asked for exactly this — "for now, just copy, will solve it later" — and the debt is
filed as [#461](https://github.com/ShishkinDmitriy/orexis/issues/461), beside
[#25](https://github.com/ShishkinDmitriy/orexis/issues/25), which is the same seam seen from
the generator. `orexis-firmware` renders this firmware through the sentinel's own template
(`render_sentinel`) plus the BME280 and WS2812 defines, so the CONFIG is not duplicated —
and the terrace is the first real run that template has had (#323 stays open until a world
deploys `moisture-sentinel` itself).

## What the sentinel is

A sentinel is **autonomous**: `sensing:PushProcedure`, so it takes no orders at all — no
command topic, no subscribe, nothing to parse — and its agent derives `sensing:Listening` and
can only receive. (The [moisture-sensor](../moisture-sensor/) node is the opposite temperament:
governed, its agent commands the cadence and the band.)

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

Type a board's connecting device `outdoor:Node` (this directory's `ontology.ttl` entails the
firmware name, the push mode and the alarm promise), give its subject an
`ssn-system:hasOperatingRange` for what it watches, run `orexis-firmware <world>`, and flash.
`world/terrace` does exactly that: a FireBeetle 2 ESP32-E on a planter bed, outdoors, the
probe on GPIO 34 (A2) and a BME280 on I2C (SDA 21, SCL 22, 0x76).

```bash
pio run -t upload      # from this directory; the one environment is the FireBeetle
pio device monitor
```

## The outdoor air sensor

Where the world wires a BME280 (`BME280_SDA_PIN`, `BME280_SCL_PIN`, `BME280_ADDR`, generated
from the wiring and the unit's `i2c:address`), every heartbeat and every alarm carries
`temperature`, `humidity` (a fraction) and `pressure` (hPa) beside `moisture`, one forced-mode
conversion per wake. `VCC → 3V3` (never 5 V — the bare part is not 5 V-tolerant), `GND → GND`,
`SDA → GPIO21`, `SCL → GPIO22`. The ULP does not watch it: I2C is a bus the coprocessor cannot
speak, and the world says so by typing only the probe's channel with the alarm promise.

## The status LED, and the FireBeetle's own

Same vocabulary as the sentinel's — two green for a wake that got in, one magenta per refused
broker attempt, three of a colour for a fault, dark through every sleep. On the sentinel's DevKitC
that is an external KY-016 the world wires (`LED_RED_PIN` and friends, still compiled here if a
world wires one). On the **FireBeetle 2 ESP32-E** it is the board's own WS2812 on GPIO 5 (`STATUS_LED_WS2812_PIN`, stated on the board class in
`packages/orexis-part-esp32/` so no world wires it), driven by the ESP32 core's RMT driver with
no extra library. There is no vigil lamp on it: the ULP's between-wakes blink needs a bare GPIO.

It exists for battery bring-up: a node meant to stay dark for months is hard to trust until it
has been seen to wake and get in. Once you have seen that, **cut the board's low-power solder
pad** — DFRobot: "Slightly cut off the thin wire with a knife to disconnect it. When
disconnected, static power consumption can be reduced by 500 μA. Note: when the pad is
disconnected, you can only drive RGB LED light via the USB Power supply"
([wiki, DFR0654](https://wiki.dfrobot.com/FireBeetle_Board_ESP32_E_SKU_DFR0654)). The firmware
keeps writing to a lamp that then draws nothing on battery, and lights again on USB — no
reflash, no world edit.

## Which firmware for battery?

Estimated from this bench's own numbers: a full radio wake (boot, WiFi, publish, release) is
~8–9 s at ~100 mA ≈ **0.25 mAh**; the ULP vigil is ~150 µA ≈ **3.6 mAh/day**. One wake buys
about a hundred minutes of watching — speaking is the cost, watching is noise.

| configuration | wakes/day | ≈ mAh/day | 2000 mAh cell |
|---|---|---|---|
| governed @ slow 600 s + watch | 144 | 40 | ~7 weeks |
| governed, realistic (bursts, verification) | 180–240 | 50–65 | ~5 weeks |
| sentinel, heartbeat 600 s | ~146 | 40 | ~7 weeks |
| sentinel, heartbeat 20 min | 72 | 21.6 | ~3 months |
| **sentinel, heartbeat 30 min** | 48 | **15.6** | **~4 months** |
| sentinel, heartbeat 40 min | 36 | 12.6 | ~5 months |
| sentinel, heartbeat 1 h | ~26 | 10 | ~6 months |
| sentinel, heartbeat 4 h | ~8 | 6 | ~11 months |

**The patrol period is not in that table, because it does not belong there.** A look costs about
2 × 10⁻⁷ mAh — start the oscillator, ~25 instructions, one conversion — so the vigil's 150 µA is
almost entirely the RTC peripheral domain standing powered for the SAR, and only ~0.8 µA of it is
looking, even at one look per second. **One radio wake buys roughly 1.1 million looks.** Patrolling
every 15 s instead of every 60 s costs about a thousandth of a mAh per day: an hour of life over a
three-month cell. So `WATCH_PATROL_S` is chosen for detection latency alone, and it is 15.

What a faster patrol *can* cost is indirect — it notices more transients, and each extra alarm is a
full 0.25 mAh wake, about 1.7 hours of standing vigil. If it ever hurts, that is the mechanism, and
`WAKE_DELTA` is the knob rather than the period. The derivation is in
[the-vigil-costs-standing-not-looking](../../knowledge/decisions/the-vigil-costs-standing-not-looking.md),
including which of these numbers are measured and which are estimated.

**The battery is spent by the agent's epistemology, not by the firmware.** The sentinel's
heartbeat is generated under the polling agent's `sensing:maxReadingAgeS`, so the same board is
either no better than the governed node or four times better depending on that one belief. The
crossing promise is what makes a generous one safe: silence means *nothing crossed*, freshness
work moves off the heartbeat onto the ULP, and the heartbeat only proves liveness. A world that
deploys a sentinel and keeps a twelve-minute freshness rule has bought the watcher and declined
the savings. Past ~4 h the vigil itself dominates (~3.6 of 6 mAh) — and *that* is now the whole of
the energy-budget seam #151 left open: the watching has been priced, it is standing cost rather
than sampling cost, and the only way left to reduce it is to stop holding the RTC domain powered
between looks.
