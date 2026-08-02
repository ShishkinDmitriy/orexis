# Agora — v1

A market society of self-interested agents that allocate a scarce resource through
iterative auctions and deliberation, under a hard trust/constitution boundary — grounded
in real sensors on a Raspberry Pi. The domain is a plug-in; the **v1 example domain is
plant watering** (agents bid for water). Architecture and rationale live in
[`knowledge/`](knowledge/) (OKF bundle). This README covers the **gateway slice** — the
first thing to build.

```
plant edge (ESP32 or agora-sim) --> InfluxDB (history) + Fuseki :sensed (self-asserted)
                                --> readings/<plant> (a new-reading event)
   agents read their own :sensed --> judge LOW --> auction --> clearing --> executor --> valve
```

Trusted-agent mode (v1): there is no gateway — each plant asserts its own reading. See
[`knowledge/decisions/trusted-agent-mode.md`](knowledge/decisions/trusted-agent-mode.md).

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

One-time, once infra is up: `agora-seed` (loads the T-Box + structure). Then, in two
terminals (venv active in both):

```bash
agora-sim              # virtual plants: sense, assert their own :sensed data, get watered
agora-round            # agents read their own :sensed, bid, host clears, grants issue
```

`agora-sim` is the plant edge — there's no gateway; each plant authors its own reading. A
round is: `plants sense → agents read their :sensed → judge LOW → auction → clearing`.
Deterministic, no LLM. (For a closed loop where wins actually water the plants, set
`executor.actuate: true`.)

For unattended operation — a round that fires automatically when a plant crosses `:LOW`,
plus systemd units that survive reboot — see [`deploy/`](deploy/). `agora-loop` is the
event-driven runner; `executor.actuate` in the config gates whether it opens valves
(`false` = sensor-only: decide and log, don't water).

## Run the whole society in simulation (no hardware)

Because the physical edge is dumb and interchangeable, **virtual plants** (soil models) are
indistinguishable from real ones to the gateway and the auction — so you can run and watch
the entire society in software, and even mix virtual + real plants. `agora-sim` replaces the
sensor edge *and* the pump: each virtual plant dries over time, publishes its moisture, and
gains moisture when it wins water — a closed loop driven by the market.

```bash
# set executor.actuate: true in backend/config/plants.yaml (the market must open valves)
agora-gateway        # attests measurements
agora-sim            # virtual plants: dry, publish readings, get watered on wins
agora-loop           # fires a round when an agent judges itself LOW
```

Watch the plants dry, hit their own LOW, win water, and recover — `journalctl`/logs show
`running a round` → grants → `watered N ml -> moisture ...`. Grafana shows the moisture
oscillate around each plant's target. To mix with real hardware, list only the *virtual*
plant ids under `simulator.plants` and give the real ones ESP32s on the same topics.

## 4. Inspect

- **Grafana dashboard** — http://localhost:3000/d/agora-moisture (or `http://<pi-ip>:3000/...`
  from another machine). No login (anonymous Viewer enabled); auto-refreshes every 5s.
  Shows current moisture per plant (colored by band) and a moisture-over-time chart. The
  dashboard and datasource are **provisioned** from `infra/grafana/` — recreating Grafana
  restores them, nothing lives only in the container.
- **Attested measurement (what agents cite)** — query Fuseki. The gateway attests the
  *number*, not a band — "is it LOW?" is each agent's own call. Query endpoint on this image
  is `/ds/sparql` (not `/ds/query`); updates go to `/ds/update`:

  ```bash
  curl -s http://localhost:3030/ds/sparql \
    --data-urlencode 'query=PREFIX sosa:<http://www.w3.org/ns/sosa/>
      SELECT ?plant ?value WHERE {
        GRAPH <http://example.org/agora/graph/sensed> {
          ?o sosa:hasFeatureOfInterest ?plant ; sosa:hasSimpleResult ?value }
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
