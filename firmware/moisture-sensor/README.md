# Moisture sensor (ESP32) — scheduled

A stake-free sensor node. It declares itself `perception:ScheduledSampling` in the world, which gives its
agent **`ag:Subscribing`**: the *agent* states the interval (how often to look), and this
board **keeps to it** — reads a capacitive soil-moisture sensor, publishes a 0..1 value,
briefly listens for a new interval, then **deep-sleeps**. Big battery savings, and the agent
still controls attention. One board per subject.

Note what this is *not*. It is not `ag:Polling`, where the agent asks for each reading and the
device replies: this board is unreachable while asleep, so a request would land on nothing.
The agent hands it a standing instruction instead of a repeated one, and that trade — giving
up "read now" to get deep sleep — is exactly why the two are separate capabilities. See
[sensing](../../knowledge/domain/sensing.md).

```
wake -> read -> publish  sensors/<subject>/moisture  {"value":0.183,"sensor":"..."}
     -> listen (retained) sensors/<subject>/cmd       {"sleep_s":N} / {"sense":true}
     -> deep-sleep sleep_s, then repeat
```

Realizes [agent-driven sensing](../../knowledge/decisions/agent-centric-epistemics.md):
**cadence ≠ content** — the agent chooses *when* to look; the reading is what the sensor
measured. The board emits **numbers only** — the band/threshold judgement is the agent's, and
lives in that agent's own beliefs (`world/<name>/beliefs/<agent>.ttl`), never in firmware. An agent
with no stake holds no band at all and simply records the number.

## The agent sets the interval

Publish a **retained** command to `sensors/<subject>/cmd` — the board reads it on each wake:

- `{"sleep_s": 300}` — sense every 5 min (clamped to `[MIN_SLEEP_S, MAX_SLEEP_S]`).
- `{"sense": true}` — take an extra reading while the board is briefly awake. **Best-effort**:
  the waking window is `CMD_WAIT_MS` (1.5s by default), so a nudge sent at any other moment is
  simply lost, and it is never retained (a retained `sense` would re-fire on every wake,
  forever). This is the seed of `ag:Polling`, not a substitute for it.

`MAX_SLEEP_S` is the **constitutional cadence floor**: the board never sleeps longer than
that, so a plant can't go blind through a drought however lazy its agent gets.

```bash
# example: ask fern's board to report every 2 minutes
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

Set WiFi, the Pi's IP as `MQTT_HOST`, the ADC pin, the cadence bounds, and calibration.

`PLANT_ID` and `SENSOR_ID` must agree with `world/<name>/world.ttl`: the topics this board uses are
built from `PLANT_ID`, and they have to be the `ag:readingTopic` / `ag:commandTopic` the world
states for the matching `ag:Sensor`, whose `ag:localId` is `SENSOR_ID`. The `"sensor"` field in each published
payload must equal that `ag:localId` — a mismatch is the failure that otherwise goes silent.

Read `ADC_DRY` (dry air) and `ADC_WET` (in water) from the monitor; the firmware maps
`dry→0.0`, `wet→1.0`.

**The broker must accept LAN connections.** Mosquitto 2.x binds to loopback only out of the
box, so a board gets `Connection refused` and it looks like a firmware fault:

```bash
cd infra && podman compose up -d mosquitto
ss -lntp | grep 1883        # expect 0.0.0.0:1883, not 127.0.0.1:1883
```

## Build & flash

```bash
pio run -t upload          # build + flash over USB
pio device monitor         # watch it wake, publish, sleep
```

## Check it works

From the Pi, without the market or any other agent running:

```bash
mosquitto_sub -h localhost -t 'sensors/fern/#' -v    # is it publishing at all?
agora-compose sensing                                # one agent, perception only
cd ../../world/sensing && podman compose up -d
```

`world/sensing` is the smallest ratified world: one subject, one board, one agent, no
market. The agent logs the interval it set, and the line appears in Grafana
(`localhost:3000`, "Agora — Moisture"). Two things to eyeball in the raw payloads: the
`"sensor"` field must match the sensor's `ag:localId` in the world, and a value pinned at
exactly `0.000` or `1.000` means `ADC_DRY`/`ADC_WET` are wrong.

Seed `society` instead and the same board, unchanged, joins a market.

## Where the readings go

There is **no gateway** in v1 (trusted-agent mode) — each agent asserts its own `:sensed`
data. The agent-side half of this board is the **perception capability**
(`capabilities/perception/`): it sets the cadence, takes the published reading, writes the
series to Influx and asserts the observation to `:sensed` under its own authorship, with the
`ag:polls` grant that entitles it to this sensor (see
[connection determines authorization](../../knowledge/decisions/authn-authz-capabilities.md)).

That capability runs alone, which is what `world/sensing` demonstrates: an agent there holds
nothing else — no market, no bidding, no stake — because that world gives it nothing else to
be wired to.

## More boards

Copy per plant (or reuse and change `PLANT_ID` / `SENSOR_ID` / calibration per flash). Each
board is independent, keyed by plant.
