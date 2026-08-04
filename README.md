# Agora — v1

A market society of self-interested agents that allocate a scarce resource through
iterative auctions and deliberation, under a hard trust/constitution boundary — grounded
in real sensors on a Raspberry Pi. The domain is a plug-in; the **v1 example domain is
plant watering** (agents bid for water). Architecture and rationale live in
[`knowledge/`](knowledge/) (OKF bundle).

**One process per agent.** Each is told only its own id and reads the rest from the belief
base — what it is wired to, what it can therefore do, and what it privately wants:

```
  agent asks its board      -> ag:commandTopic   {"sense":true} | {"sleep_s":N} retained
  board answers             -> ag:readingTopic   {"value":0.183,...}
  agent records + announces -> :sensed + Influx, then ag:eventTopic {"band":"LOW"}
  host opens a round        -> ag:offerTopic     quantity, reserve, deadline
  each bidder answers       -> ag:bidTopic/<id>  a number only it can compute
  host clears, vouchers go  -> ag:voucherTopic/<id>  -> owner opens its own valve
```

Nothing above is a name in the code. Every channel, every device, every limit is read from
the graph; the one instance identifier a process gets is its own agent id.

Agents are configured by **belief, not by file**. `:world` holds the public wiring — and from
that wiring genesis *derives* what each agent can do, so a scheduled sensor gives its agent a
cadence to own and a push-mode one does not. `:beliefs/<agent>` holds what each privately
wants. See [`capability-modules`](knowledge/decisions/capability-modules.md) and
[`world-graph`](knowledge/decisions/world-graph.md).

Trusted-agent mode (v1): there is no gateway — each plant asserts its own reading. See
[`knowledge/decisions/trusted-agent-mode.md`](knowledge/decisions/trusted-agent-mode.md).

Sensing is **agent-timed**: the board only senses and sleeps; the *agent* decides how often to
look, and bids only on a fresh reading. See
[`knowledge/domain/sensing.md`](knowledge/domain/sensing.md).

## Layout

```
kernel/        the T-Box everything layers on. Not a capability; there is one
capabilities/  what an agent can DO — perception, market, actuation. The extendable axis
transports/    how a device is REACHED — mqtt. Deliberately not a capability
domain/        what the society is ABOUT — water. Vocabulary; the domain is a plug-in
backend/       the runtime that loads all of the above, plus the pure market mechanism
genesis/       ratified worlds — one directory each, complete and seedable on its own
firmware/      ESP32 edge — moisture sensors and pump/valve
infra/         compose service configs — grafana, mosquitto
knowledge/     OKF knowledge bundle (architecture decisions + domain model)
```

**A capability is a directory**, and inside it the same names mean the same things every
time:

```
capabilities/perception/
  ontology.ttl   the vocabulary — what its terms mean
  shapes.ttl     the rules — what an agent must believe to hold it
  rules.ru       the derivation — what wiring GIVES an agent it
  terms.py       the terms it implements, and the families it asks others for
  beliefs.py     its Blocks — the private parameters it reads
  module.py      the code, which reads only that vocabulary
  __init__.py    the manifest: PROVIDES = (PollingModule, ListeningModule)
```

Every one of them is optional, and an omission is a statement: `domain/water/` has no code,
`transports/mqtt/` has no `rules.ru` because a transport grants no capability, and
`capabilities/actuation/` has no `beliefs.py` because it decides nothing.

Nothing lists these — `agora.loader` finds them by looking. So **adding a capability is
adding a directory**: drop in `capabilities/forecast/`, and `agora-seed` loads its vocabulary,
runs its derivation, and agents that the wiring qualifies boot with it. No registry line, no
term constant, no edit to any existing file — and deleting the directory removes it just as
completely, because capabilities reach each other through T-Box terms and never through
Python imports. See
[`capability-packages`](knowledge/decisions/capability-packages.md).

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

Fuseki serves the belief base behind **two doors**, because Jena's per-graph access control is
read-only: `/ds` is the secured one an agent reads through as itself, `/ds-rw` takes writes
(updates from any agent, whole-graph operations from admin only). Its config is generated —
see `agora-acl` below — and its data is in a named volume, so rebuilding the container does
not destroy the world.

**MQTT runs on the host, not in a container.** The Alpine/musl `eclipse-mosquitto` image
can't open a config file on the Pi's kernel under rootless Podman/overlay; the Debian
(glibc) build has no such issue, and since the agents are host processes anyway, a host
broker is the clean choice:

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

One-time setup, in order:

```bash
agora-acl              # one isolated Fuseki dataset per world + per-agent credentials
                       #   (re-run after adding a world or agent; restart Fuseki to load it)
agora-keygen           # the host + clearing signing keys the valves check
agora-seed society     # the belief base itself
```

`agora-seed` takes **which world** to load. [`genesis/`](genesis/) holds one directory per
ratified world, each complete on its own: `society` is the full example, `sensing` is the
smallest one that produces a working agent. [`domain/world`](knowledge/domain/world.md) is the
guide to authoring your own — what a world is made of, what you state versus what gets
derived, and how to check it.

`agora-acl` is what makes privacy real rather than polite: it reads who exists from that
world and writes a Fuseki access list granting each agent the shared graphs plus
its *own* beliefs — so `fern` querying `:beliefs/tomato` gets nothing back. Credentials land
in `keys/fuseki/` (gitignored); each agent reads its own. See
[`belief-base-isolation`](knowledge/decisions/belief-base-isolation.md).

`agora-seed` then loads the T-Box, the **world** (wiring), **derives each agent's
capabilities** from that wiring, and loads each agent's **private beliefs** from
[`genesis/`](genesis/). It prints what it derived:

```
derived fern      -> Bidding, Subscribing
derived supplier  -> Hosting, Actuation
```

Then bring the society up. **Agents are not launched from a list — they are born from the
world**, one process each:

```bash
agora-compose society                                  # generate the compose file FROM the world
cd deploy && podman compose -f compose.society.yml up -d
agora-sim                                              # virtual plants, if you have no hardware
```

```
born  fern       Bidding, Subscribing
born  succulent  Bidding, Subscribing
born  supplier   Hosting, Actuation
born  tomato     Bidding, Subscribing
```

The roster is the ratified world, so a different world brings up a different society with no
edit anywhere — `agora-compose sensing` yields exactly one agent that only watches.
`AGORA_AGENT_ID=fern agora-agent` is still the primitive underneath; the container merely sets
that variable.

**One container per agent, and that is the point.** On one filesystem every agent could read
every other agent's store credential out of `keys/fuseki/`, making the per-graph ACL a
convention. Each container mounts exactly one `.pw` — its own — and only the agent that derived
`ag:Actuation` is given the signing keys. See
[`domain/world`](knowledge/domain/world.md) §Deployment.

Note what is *not* born this way: firmware. A board is hardware and is flashed by hand. What
the model decides is what an **agent** is — which is why the same flashed board is a watcher
in one world and a bidder in another.

Each agent boots from its id alone: it reads the world (*what am I wired to, and what does
that let me do?*), then its own beliefs (*what do I want, how closely should I watch?*), and
runs exactly the modules its capabilities name. A round is a conversation — a plant announces
its own verdict, the host offers, bidders answer with numbers only they can compute, clearing
validates, vouchers come back. Deterministic, no LLM. (For a closed loop where wins actually
water the plants, set `AGORA_ACTUATE=true`.)

A bidder **looks before it bids** and sits out the round if its sensor does not answer in
time, or if the newest reading is older than its own `ag:maxReadingAgeS`. Owning the cadence
must not mean bidding on a stale, comfortable number — and the limit is each agent's own
belief, so a slow-living succulent may accept older data than a fern.

For unattended operation — one systemd unit per agent, surviving reboot — see
[`deploy/`](deploy/). `AGORA_ACTUATE` in `.env` gates whether the supplier actually opens
valves (`false` = sensor-only: decide, log, water nothing). Deployment toggles like this stay
in the environment — they are about the physical installation, not beliefs anyone holds.

## Run the whole society in simulation (no hardware)

Because the physical edge is dumb and interchangeable, **virtual plants** (soil models) are
indistinguishable from real ones to the agents and the auction — so you can run and watch
the entire society in software, and even mix virtual + real plants. `agora-sim` replaces the
sensor edge *and* the pump: each virtual plant dries over time, senses on the cadence its
agent set, and gains moisture when it wins water — a closed loop driven by the market.

```bash
# set AGORA_ACTUATE=true in .env (the supplier must be allowed to open valves)
agora-sim      # virtual plants: dry, sense on their agent's interval, get watered
cd deploy && podman compose -f compose.society.yml up -d   # the whole society
```

Watch the plants dry, hit their own LOW, win water, and recover — `journalctl`/logs show
`running a round` → grants → `watered N ml -> moisture ...`. Grafana shows the moisture
oscillate around each plant's target. To mix with real hardware, list only the *virtual*
plant ids in `AGORA_SIM_PLANTS` and give the real ones ESP32s on the same topics.

## 4. Inspect

- **Grafana dashboard** — http://localhost:3000/d/agora-moisture (or `http://<pi-ip>:3000/...`
  from another machine). No login (anonymous Viewer enabled); auto-refreshes every 5s.
  Shows current moisture per plant (colored by band) and a moisture-over-time chart. The
  dashboard and datasource are **provisioned** from `infra/grafana/` — recreating Grafana
  restores them, nothing lives only in the container.
- **Sensed measurement (what agents cite)** — query Fuseki. `:sensed` holds the *number* and
  the time it was taken, never a band — "is it LOW?" is each agent's own call, and "is it
  still true?" is the freshness gate's. Query endpoint on this image is `/ds/sparql` (not
  `/ds/query`); updates go to `/ds/update`:

  ```bash
  curl -s http://localhost:3030/ds/sparql \
    --data-urlencode 'query=PREFIX sosa:<http://www.w3.org/ns/sosa/>
      SELECT ?plant ?value WHERE {
        GRAPH <http://example.org/agora/graph/sensed> {
          ?o sosa:hasFeatureOfInterest ?plant ; sosa:hasSimpleResult ?value }
      }' \
    -H 'Accept: text/csv'
  ```

## Bringing a real board up

Seed the **smallest world** instead of the society. `genesis/sensing` has one subject, one
board and one agent, plumbed into no market — so derivation gives that agent `ag:Subscribing`
and nothing else. It reads, records, and stops. Nothing in that world declares it sensor-only;
there is simply no market for a market capability to come from.

```bash
sudo cp infra/mosquitto/lan.conf /etc/mosquitto/conf.d/agora.conf   # mosquitto 2.x binds to
sudo systemctl restart mosquitto                                    # loopback until told not to

agora-seed sensing && agora-compose sensing            # one agent, perception only
cd deploy && podman compose -f compose.sensing.yml up -d
mosquitto_sub -t 'sensors/#' -v      # or just watch the wire
```

The device ids and channels are identical in both worlds on purpose, so **the board needs no
reflash**: seed `society` and the very same hardware joins a market. The model changed, not
the firmware.

A scheduled board is asleep almost all the time, so silence usually means it is working —
wait one interval. The interval is retained and therefore reliable; `{"sense":true}` is
best-effort and lands only if the board happens to be awake.

## Real hardware

A real ESP32 speaks the same protocol as a virtual plant — an agent can't tell them apart, so
you can mix them freely:

- publishes on its `ag:readingTopic` — `{"value": 0.18, "sensor": "moisture_sensor_fern"}`
- subscribes to its `ag:commandTopic` — `{"sleep_s": 300}` (retained) and/or `{"sense": true}`

Both topics are whatever `genesis/world.ttl` says they are; nothing is derived from the id.

Declare the board's nature with `ag:senseMode`, and the capability follows from it — the axis
is **who holds the clock**:

| `ag:senseMode` | capability | who runs the timer |
|---|---|---|
| `ag:Pull` | `ag:Polling` — *reserved, not built* | the agent asks for each reading |
| `ag:Scheduled` | `ag:Subscribing` | the agent sets an interval, the board keeps it |
| `ag:Push` | `ag:Listening` | the board, alone |

`ag:Polling` is the simplest exchange and what the word ought to mean, but it needs a board
reachable at any moment — one that deep-sleeps cannot hear the request. So it is declared in
the vocabulary with no rule granting it and no module providing it. The room is kept on
purpose; adding it is a class and one line of `PROVIDES`.

The ESP32 firmware is `ag:Scheduled`. Change the firmware, re-run `agora-seed`, and the
capability changes with it — the agent is never edited.

The board holds no policy. Bands, cadence, and prices are the agent's own beliefs
([`genesis/beliefs-<agent>.ttl`](genesis/)); the wiring and the valve calibration are the
world's ([`genesis/world.ttl`](genesis/world.ttl)). Edit and re-run `agora-seed` — no reflash.
The one thing firmware *does* enforce is the constitutional cadence clamp
(`MIN_SLEEP_S`/`MAX_SLEEP_S` in `config.h`) — a buggy agent must not be able to talk a board
into sleeping through a drought.

## Tests

The market layer (`clearing`, `auction`) is pure (no infra, no LLM), so it's fully unit-tested:

```bash
pip install -e "./backend[dev]"
pytest backend -q
```

Validate the live belief base against every package's `shapes.ttl`. The checks
are **capability-aware**: a rule applies to an agent only if the world derived that capability
for it. So the supplier is never asked for a cadence, a polling agent must have one, and a
listening agent must *not* — plus the usual: a band whose floor is below its ceiling, a
cadence that watches more closely when thirsty, nobody sleeping past the constitutional
ceiling, and every device stating where it is reachable.

```bash
agora-validate         # every package's shapes over :world + :beliefs/* + :sensed
```

## What's next

Built: belief base ✓ (modular T-Box + `:world` + `:beliefs/<agent>` + `:sensed`,
typed/versioned/SHACL-clean, and the only source of configuration), capability modules ✓
(vocabulary + rules + derivation + code, with abilities derived from hardware), one process
per agent ✓, the distributed round ✓, `sensing` ✓
(agent-driven: the agent sets the cadence and bids only on a fresh reading), `agent` ✓
(deterministic bids from live `:sensed`), `auction` ✓, `clearing` ✓ (validator + grant),
`executor` ✓ (grant → bounded valve command, `jti` single-use), and firmware for both edges
(moisture sensor, guarded pump/valve). The loop closes: **sensor-in → water-out**.

Next: the **LLM stance** layer (justification/coalition on top of the deterministic number —
the leash), wallet debiting + metabolic cost — which is also what makes *perception* a priced
action, the one part of agent-driven sensing still missing — and the constitution as SHACL
over the trade.
See [`knowledge/decisions/roadmap.md`](knowledge/decisions/roadmap.md).
