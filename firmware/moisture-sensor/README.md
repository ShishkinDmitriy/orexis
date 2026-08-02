# Moisture sensor (ESP32) — pull-based

A stake-free sensor node, **pull-based**: the *agent* owns the cadence (how often to look),
the board provides the mechanism (sense + sleep). Each wake it reads a capacitive
soil-moisture sensor, publishes a 0..1 value, briefly listens for an agent-set cadence, then
**deep-sleeps** — big battery savings, and the agent controls attention. One board per plant.

```
wake -> read -> publish  sensors/<plant>/moisture  {"value":0.183,"sensor":"..."}
     -> listen (retained) sensors/<plant>/cmd       {"sleep_s":N} / {"sense":true}
     -> deep-sleep sleep_s, then repeat
```

Realizes [agent-driven sensing](../../knowledge/decisions/agent-centric-epistemics.md):
**cadence ≠ content** — the agent chooses *when* to look; the reading is what the sensor
measured. The board emits **numbers only** — the band/threshold judgement is the agent's
(`backend/config/plants.yaml`), never in firmware.

## The agent sets the cadence

Publish a **retained** command to `sensors/<plant>/cmd` — the board reads it on each wake:

- `{"sleep_s": 300}` — sense every 5 min (clamped to `[MIN_SLEEP_S, MAX_SLEEP_S]`).
- `{"sense": true}` — take an extra reading while the board is briefly awake.

`MAX_SLEEP_S` is the **constitutional cadence floor**: the board never sleeps longer than
that, so a plant can't go blind through a drought however lazy its agent gets.

```bash
# example: ask fern's sensor to report every 2 minutes
mosquitto_pub -h <pi> -r -t sensors/fern/cmd -m '{"sleep_s":120}'
```

## Wiring

- Capacitive soil-moisture sensor: `VCC → 3V3`, `GND → GND`, `AOUT → GPIO34`.
- Use an **ADC1** pin (GPIO 32–39); ADC2 pins don't work with WiFi on. GPIO 34–39 are
  input-only, which is fine here.

## Configure & calibrate

```bash
cp include/config.h.example include/config.h    # gitignored (WiFi secrets)
```

Set WiFi, the Pi's IP as `MQTT_HOST`, `PLANT_ID` (must match `backend/config/plants.yaml`),
the ADC pin, the cadence bounds, and calibration. Read `ADC_DRY` (dry air) and `ADC_WET` (in
water) from the monitor; the firmware maps `dry→0.0`, `wet→1.0`.

## Build & flash

```bash
pio run -t upload          # build + flash over USB
pio device monitor         # watch it wake, publish, sleep
```

## Where the readings go (post-gateway)

There is **no gateway** in v1 (trusted-agent mode) — each plant asserts its own `:sensed`
data. So a **networked** real sensor needs an agent-side reader that (a) sets this board's
cadence and (b) takes the published reading and asserts it to `:sensed` (with the plant's
**access grant**, since it's over the network — see
[connection determines authorization](../../knowledge/decisions/authn-authz-capabilities.md)).
That agent-side networked-sensor bridge is the remaining integration; the firmware here is
the device mechanism. A sensor wired **directly** to the plant's own Pi needs none of this —
the agent reads it locally.

## More boards

Copy per plant (or reuse and change `PLANT_ID` / `SENSOR_ID` / calibration per flash). Each
board is independent, keyed by plant.
