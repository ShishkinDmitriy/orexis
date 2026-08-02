# Pump / valve (ESP32)

The actuation edge: a **guarded** MQTT subscriber that drives a relay/valve on executor
commands, with a fail-safe watchdog. One board per plant valve.

```
executor (Pi) --publish--> actuators/<plant>/valve --subscribe--> ESP32 --> relay/valve
                        <-- actuators/<plant>/valve/status <--
```

Because actuation is physically irreversible, this board is dumb but *guarded*
(see [`knowledge/domain/executor.md`](../../knowledge/domain/executor.md)):

- **Commands only from the executor topic** — v1 trusts the LAN; v2 verifies a signed grant.
- **jti dedup** — a redelivered command (MQTT QoS 1) never double-waters.
- **Fail-safe watchdog** — the valve never stays open past `MAX_OPEN_SECONDS`, and closes on
  any lost WiFi/MQTT connection. A hard local cap, whatever a command says.
- **Status publish** — reports open/close so the executor knows water actually flowed.

## Wiring

- Relay module: `VCC → 5V` (or 3V3 per module), `GND → GND`, `IN → GPIO26`.
- Pump/solenoid valve switched by the relay (use a separate supply for the pump).
- Set `VALVE_ACTIVE_HIGH` to match your relay (some open on LOW).

## Configure

```bash
cp include/config.h.example include/config.h    # gitignored (WiFi secrets)
```

Set WiFi, the Pi's IP as `MQTT_HOST`, `PLANT_ID` (matches `backend/config/plants.yaml`),
`VALVE_PIN`, and — importantly — `MAX_OPEN_SECONDS` (the hard fail-safe) and `ML_PER_SECOND`
(for the status estimate; the executor does the real litres→seconds calibration).

## Build & flash

```bash
pio run -t upload
pio device monitor
```

## Test without hardware

Watch commands and fake the board with the mosquitto clients on the Pi:

```bash
mosquitto_sub -t 'actuators/#' -v          # see executor commands + status
mosquitto_pub -t actuators/fern/valve -m '{"jti":"t1","plant":"fern","seconds":3}'
```

The `agora-round` command publishes real valve commands after clearing goes green.
