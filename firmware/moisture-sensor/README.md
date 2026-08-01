# Moisture sensor (ESP32)

A stake-free sensor node: reads a capacitive soil-moisture sensor and publishes a 0..1
value to MQTT for the [gateway](../../knowledge/domain/gateway.md). One board per plant.

```
sensor --ADC--> ESP32 --MQTT--> sensors/<plant>/moisture  {"value":0.183,"sensor":"..."}
```

The board emits **numbers only** — the band/threshold judgement lives on the Pi
(`backend/config/plants.yaml`), never in firmware. Recalibrate there, no reflash.

## Wiring

- Capacitive soil-moisture sensor: `VCC → 3V3`, `GND → GND`, `AOUT → GPIO34`.
- Use an **ADC1** pin (GPIO 32–39); ADC2 pins don't work with WiFi on. GPIO 34–39 are
  input-only, which is fine here.

## Configure

```bash
cp include/config.h.example include/config.h    # config.h is gitignored (WiFi secrets)
```

Edit `include/config.h`: WiFi, the Pi's IP as `MQTT_HOST`, `PLANT_ID` (must match an id in
`backend/config/plants.yaml`), the ADC pin, and calibration.

## Calibrate

Flash, open the monitor, and read the raw values at two extremes:

- **ADC_DRY** — sensor in dry air / bone-dry soil (highest reading).
- **ADC_WET** — sensor fully submerged / saturated soil (lowest reading).

Put those in `config.h`. (A capacitive sensor reads high when dry, low when wet — the
firmware maps `dry→0.0`, `wet→1.0`.)

## Build & flash

With [PlatformIO](https://platformio.org/):

```bash
pio run -t upload          # build + flash over USB
pio device monitor         # watch it publish
```

Then on the Pi, `agora-gateway` will pick the readings straight off MQTT — the same topic
and payload the `agora-fake-sensor` used, so it's a drop-in replacement for real hardware.

## More boards

Copy this project per plant (or reuse it and just change `PLANT_ID` / `SENSOR_ID` /
calibration per flash). Each board is independent; the gateway keys readings by plant.
