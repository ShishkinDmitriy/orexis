# Agora — v1

A market society of self-interested agents that allocate a scarce resource through
iterative auctions and deliberation, under a hard trust/constitution boundary — grounded
in real sensors on a Raspberry Pi. The domain is a plug-in; the **v1 example domain is
plant watering** (agents bid for water). Architecture and rationale live in
[`knowledge/`](knowledge/) (OKF bundle). This README covers the **gateway slice** — the
first thing to build.

```
ESP32 (or fake_sensor) --moisture--> MQTT --> gateway --> InfluxDB (series)
                                                    \--> Fuseki   (:attested current-state)
                                                    \--> situations/<plant> (band-change event)
```

## Layout

```
backend/     Python on the Raspberry Pi — gateway, market (clearing/auction), agents
firmware/    ESP32 edge — moisture sensors (and later actuators)
infra/       compose service configs — grafana, mosquitto
knowledge/   OKF knowledge bundle (architecture decisions + domain model)
```

## Prerequisites

- Docker + Compose, **or** Podman + `podman-compose` (both work — the compose file is
  plain Compose-spec, rootless-friendly)
- Python 3.10+
- Mosquitto MQTT broker on the host (see below)

## 1. Infra

```bash
cp .env.example .env
docker compose up -d        # or: podman compose up -d
```

Brings up: InfluxDB (`:8086`), Grafana (`:3000`), Fuseki (`:3030`). Grafana is pre-wired
to InfluxDB (anonymous viewer enabled).

**MQTT runs on the host, not in a container.** The Alpine/musl `eclipse-mosquitto` image
can't open a config file on the Pi's kernel under rootless Podman/overlay; the Debian
(glibc) build has no such issue, and since the gateway/agents are host processes anyway, a
host broker is the clean choice:

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
```

The default config listens on `localhost:1883` and accepts anonymous local connections —
which is all v1 needs (everything talks over loopback on the Pi).

## 2. App

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./backend
```

## 3. Run the slice

Two terminals (venv active in both):

```bash
agora-gateway          # subscribes to sensors/+/moisture, writes both stores
agora-fake-sensor      # simulates the ESP32 edge (no hardware needed)
```

The gateway logs `situation:` lines when a plant's band crosses LOW/OK/HIGH.

With those two running, drive a full market round from the live attested state:

```bash
agora-round            # agents read :attested, bid, host clears, grants issue
```

This is the whole loop end to end: `sensor → gateway → :attested → agents bid →
auction → clearing`. Deterministic, no LLM.

## 4. Inspect

- **Grafana dashboard** — http://localhost:3000/d/agora-moisture (or `http://<pi-ip>:3000/...`
  from another machine). No login (anonymous Viewer enabled); auto-refreshes every 5s.
  Shows current moisture per plant (colored by band) and a moisture-over-time chart. The
  dashboard and datasource are **provisioned** from `infra/grafana/` — recreating Grafana
  restores them, nothing lives only in the container.
- **Attested current-state (what agents will cite)** — query Fuseki. Note the query
  endpoint on this image is `/ds/sparql` (not `/ds/query`); updates go to `/ds/update`:

  ```bash
  curl -s http://localhost:3030/ds/sparql \
    --data-urlencode 'query=PREFIX ag:<http://example.org/agora#>
      SELECT ?plant ?band WHERE {
        GRAPH <http://example.org/agora/graph/attested> { ?plant ag:hasCurrentMoisture ?band }
      }' \
    -H 'Accept: text/csv'
  ```

## Real hardware

Point a real ESP32 at the same MQTT topic + payload shape:

- topic: `sensors/<plant_id>/moisture`
- payload: `{"value": 0.18, "sensor": "moisture_sensor_fern"}`

The threshold→band mapping stays in [`backend/config/plants.yaml`](backend/config/plants.yaml)
on the Pi — never in ESP32 firmware. Recalibrate there, no reflash.

## Tests

The market layer (`clearing`, `auction`) is pure (no infra, no LLM), so it's fully unit-tested:

```bash
pip install -e "./backend[dev]"
pytest backend -q
```

Validate the live belief base against the SHACL shapes (`ontology/shapes.ttl`) — every
attested observation must be complete, gateway-signed, and world-versioned:

```bash
agora-validate         # SHACL over :attested + :structure; exit 0 = conforms
```

## What's next

Built: `gateway` ✓, belief base ✓ (T-Box + structure + attested, typed/versioned/SHACL-clean),
`agent` ✓ (deterministic bids from live `:attested`), `auction` ✓, `clearing` ✓ (validator +
grant), `executor` ✓ (grant → bounded valve command, `jti` single-use), and firmware for both
edges (moisture sensor, guarded pump/valve). The loop closes: **sensor-in → water-out**.

Next: the **LLM stance** layer (justification/coalition on top of the deterministic number —
the leash), wallet debiting + metabolic cost, and the constitution as SHACL over the trade.
See [`knowledge/decisions/roadmap.md`](knowledge/decisions/roadmap.md).
