# Agora — v1

A market society of self-interested agents that allocate a scarce resource through
iterative auctions and deliberation, under a hard trust/constitution boundary — grounded
in real sensors on a Raspberry Pi. The domain is a plug-in; the **v1 example domain is
plant watering** (agents bid for water). Architecture and rationale live in
[`knowledge/`](knowledge/) (OKF bundle).

**One process per agent.** Each is told only its own id and reads the rest from the belief
base — what it is wired to, what it can therefore do, and what it privately wants:

```
  agent asks its board      -> mqtt:commandTopic   {"sense":true} | {"sleep_s":N} retained
  board answers             -> mqtt:readingTopic   {"value":0.183,...}
  agent records + announces -> :sensed + Influx, then ag:eventTopic {"band":"LOW"}
  host opens a round        -> ag:offerTopic     quantity, reserve, deadline
  each bidder answers       -> ag:bidTopic/<id>  a number only it can compute
  host clears, claims go  -> ag:claimTopic/<id>  -> owner opens its own valve
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
packages/      EVERY package there is, one mechanic: packages/<family>/<name>/
  core/          the base vocabulary everything layers on
  bus/  part/    protocols, and the physical things — dht11, esp32, the probe
  plant/         what this society is about: the domain, and a species
  tool/          vocabularies a generator reads, not the society
  capability/    what an agent can DO — sensing, market, actuation. The extendable axis
  transport/     how a device is REACHED — mqtt. Deliberately not a capability
  codec/  scaling/   how bytes become a document, and a document a quantity
agent/         the KERNEL that loads packages: store, genesis, runtime, inference, validate
onboarding/    the sovereign's tools: what turns a ratified world into a running society
tests/         the two gates, plus the layering the image depends on
world/         ratified worlds — one directory each: topology, beliefs, and its compose file
firmware/      ESP32 edge — moisture sensors and pump/valve
infra/         how it runs: the infra compose, grafana and mosquitto configs
knowledge/     OKF knowledge bundle (architecture decisions + domain model)
```

**A directory is a PACKAGE** — not a capability. The two are not the same axis, and saying it
the other way hid that: `packages/capability/market/` provides three capabilities, and
`packages/part/esp32/` provides none. What isolates a capability is `PROVIDES` and its term.
Inside a package the same names mean the same things every time:

```
packages/capability/sensing/
  ontology.ttl   the vocabulary — what its terms mean
  shapes.ttl     the rules — what an agent must believe to hold it
  rules.ru       the derivation — what wiring GIVES an agent it
  terms.py       the terms it implements, and the families it asks others for
  beliefs.py     its Blocks — the private parameters it reads
  module.py      the code, which reads only that vocabulary
  __init__.py    the manifest: PROVIDES = (PollingModule, ListeningModule)
```

Every one of them is optional, and an omission is a statement: `packages/plant/water/` has no code,
`packages/transport/mqtt/` has no `rules.ru` because a transport grants no capability, and
`packages/capability/actuation/` has no `beliefs.py` because it decides nothing.

Nothing lists these — `agent.loader` finds them by looking, two levels down, and the
FAMILY is the parent directory rather than anything declared. So **adding a capability is
adding a directory**: drop in `packages/capability/forecast/`, and agents load its vocabulary, run its
derivation, and boot with it if the wiring qualifies them. No registry line, no
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
cp infra/.env.example infra/.env                      # where the series store is (no secret)
cp infra/admin.env.example infra/secrets/admin.env    # the admin token — fill it in
agora-mqtt society                                    # the broker's ACL, before it can start
cd infra && docker compose up -d                      # or: podman compose up -d
```

Brings up: MQTT (`:1883`), InfluxDB (`:8086`) and Grafana (`:3000`). **No triplestore** — each agent holds its
own belief base inside its own container. Grafana is pre-wired to InfluxDB over a **read-only** token, requires a login, and serves
HTTPS with a certificate from the installation CA — so your browser will warn until you trust
`infra/secrets/ca.crt`.

**MQTT is built here rather than pulled**, and **the broker refuses anonymous clients**: every
agent and every board connects as itself, and may reach only the topics the world wires it to.
Both files behind that are generated by `agora-mqtt` from the worlds' own wiring, so it must run
before the broker will start.

`infra/mosquitto/Containerfile` is Debian + the stock `mosquitto` package. It is built rather
than pulled so the version is pinned — an upgrade should be a decision, not a side effect of
rebuilding — and so `entrypoint.sh` can keep a root shell as PID 1, which is what lets
`agora-mqtt` reload the ACL without dropping a single connected agent.

**Do not install the `mosquitto` server package on the host.** It ships
`/etc/apparmor.d/mosquitto`, a profile bound to `/usr/sbin/mosquitto` — and a profile attaches to
an executable *path*, so it confines the **container's** broker too. It permits `/etc/mosquitto/*`
and `conf.d/**` and nothing else, and under `abi <abi/4.0>` it denies every signal sent to the
process. That one artifact caused all of it: the Alpine image (config under `/mosquitto/config/`)
could not read its config by *any* means, `--privileged` changed nothing because it does not lift
AppArmor, rootless podman cannot opt out via `--security-opt apparmor=unconfined`, and
`podman stop` took 10s before escalating to `SIGKILL` — an unclean shutdown that risks the
retained cadences the persistence volume exists to keep. It was never musl, and it is not the
[upstream reports](https://github.com/eclipse-mosquitto/mosquitto/issues/2557) either.

With the package removed, stop takes 1s and exits 0. `mosquitto-clients` is safe — the profile
is not in it. Generated files are still mounted directly in `/etc/mosquitto` rather than a
subdirectory, which costs nothing and keeps the layout working if a profile ever returns.

Install `mosquitto-clients` on the host for `mosquitto_sub`/`mosquitto_pub` — the broker itself
is a container:

```bash
sudo apt install -y mosquitto-clients
```

If a **host** mosquitto is running from an earlier setup, disable it or it holds `:1883`:
`sudo systemctl disable --now mosquitto`.

## 2. App

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 3. Run the slice

One-time setup, in order:

```bash
agora-keygen society   # that world's host + clearing signing keys, once
agora-validate society # build the world from its files and check it
```

[`world/`](world/) holds one directory per ratified world, each complete on its own:
`society` is the full example, `sensing` is the smallest one that produces a working agent.
[`domain/world`](knowledge/domain/world.md) is the guide to authoring your own — what a world
is made of, what you state versus what gets derived, and how to check it.

**There is nothing to seed and no store to provision.** A world is Turtle; each agent builds its
own belief base from it at boot and keeps it in a volume of its own, which nothing else can
open. Privacy is structural rather than enforced — see
[`where-the-belief-base-lives`](knowledge/decisions/where-the-belief-base-lives.md).

Each agent, at boot, loads the T-Box and the **world** (wiring), **derives its capabilities**
from that wiring, and writes its **private beliefs** once if it has none. `agora-validate` does
the same thing without running anything, and prints what it derived:

```
derived fern      -> Bidding, Subscribing
derived supplier  -> Hosting, Actuation
```

Then bring the society up. **Agents are not launched from a list — they are born from the
world**, one process each:

```bash
agora-onboard society                                  # credentials, ACL and the compose file FROM the world
cd world/society && podman compose up -d
```

```
born  fern       Bidding, Subscribing
born  succulent  Bidding, Subscribing
born  supplier   Hosting, Actuation
born  tomato     Bidding, Subscribing
```

The roster is the ratified world, so a different world brings up a different society with no
edit anywhere — `agora-onboard sensing` yields exactly one agent that only watches.
`AGORA_AGENT_ID=fern agora-agent` is still the primitive underneath; the container merely sets
that variable.

**One container per agent, and that is the point.** On one filesystem every agent could read
every other agent's beliefs. Now each agent's belief base is a file in its own volume, locked
by its owner and unopenable by anything else — including you. Only the agent that derived
`actuation:Actuation` is given the signing keys. See
[`domain/world`](knowledge/domain/world.md) §Deployment.

Note what is *not* born this way: firmware. A board is hardware and is flashed by hand. What
the model decides is what an **agent** is — which is why the same flashed board is a watcher
in one world and a bidder in another.

Each agent boots from its id alone: it reads the world (*what am I wired to, and what does
that let me do?*), then its own beliefs (*what do I want, how closely should I watch?*), and
runs exactly the modules its capabilities name. A round is a conversation — a plant announces
its own verdict, the host offers, bidders answer with numbers only they can compute, clearing
validates, claims come back. Deterministic, no LLM. (For a closed loop where wins actually

A bidder **looks before it bids** and sits out the round if its sensor does not answer in
time, or if the newest reading is older than its own `sensing:maxReadingAgeS`. Owning the cadence
must not mean bidding on a stale, comfortable number — and the limit is each agent's own
belief, so a slow-living succulent may accept older data than a fern.

For unattended operation see [`runbooks/run-a-world`](knowledge/runbooks/run-a-world.md)
§Unattended — there are no agora services, only podman's own restart handling.

## Running without hardware

Not by running a simulator beside the agents — there isn't one any more, and there was no good
place to put it. A program pretending to be hardware had to be told which subjects to pretend
to be, and getting that wrong put two publishers on one topic with both readings ingested.

**A simulation is a world.** The model already says what every device is and how it is driven;
a device that is simulated is a *kind of device*, so an agent derives a simulated capability
from it exactly as it derives any other. Nothing is toggled, nothing is passed a flag, and a
world cannot disagree with how it is actually running.

**That world does not exist yet** — the capability and its binding are unbuilt, so today the
society needs real boards. See [`domain/world`](knowledge/domain/world.md) §Simulation.

## 4. Inspect

- **Grafana dashboard** — http://localhost:3000/d/agora-moisture (or `http://<pi-ip>:3000/...`
  from another machine). No login (anonymous Viewer enabled); auto-refreshes every 5s.
  Shows current moisture per plant (colored by band) and a moisture-over-time chart. The
  dashboard and datasource are **provisioned** from `infra/grafana/` — recreating Grafana
  restores them, nothing lives only in the container.
- **Sensed measurement (what agents cite)** — lives inside each agent and cannot be queried
  from outside; that is the isolation. `:sensed` holds the *number* and
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

Seed the **smallest world** instead of the society. `world/sensing` has one subject, one
board and one agent, plumbed into no market — so derivation gives that agent `sensing:Subscribing`
and nothing else. It reads, records, and stops. Nothing in that world declares it sensor-only;
there is simply no market for a market capability to come from.

```bash
agora-onboard sensing                                 # one agent, sensing only
cd world/sensing && podman compose up -d
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

- publishes on its `mqtt:readingTopic` — `{"value": 0.18, "sensor": "moisture_sensor_fern"}`
- subscribes to its `mqtt:commandTopic` — `{"sleep_s": 300}` (retained) and/or `{"sense": true}`

Both topics are whatever `world/<name>/world.ttl` says they are; nothing is derived from the id.

Declare the board's nature with `sensing:senseMode`, and the capability follows from it — the axis
is **who holds the clock**:

| `sensing:senseMode` | capability | who runs the timer |
|---|---|---|
| `sensing:PolledProcedure` | `sensing:Polling` — *reserved, not built* | the agent asks for each reading |
| `sensing:ScheduledProcedure` | `sensing:Subscribing` | the agent sets an interval, the board keeps it |
| `sensing:PushProcedure` | `sensing:Listening` | the board, alone |

`sensing:Polling` is the simplest exchange and what the word ought to mean, but it needs a board
reachable at any moment — one that deep-sleeps cannot hear the request. So it is declared in
the vocabulary with no rule granting it and no module providing it. The room is kept on
purpose; adding it is a class and one line of `PROVIDES`.

The ESP32 firmware is `sensing:ScheduledProcedure`. Change the firmware, edit `sensing:senseMode`, restart the
agent, and the capability changes with it — the agent is never edited.

The board holds no policy. Bands, cadence, and prices are the agent's own beliefs
([`world/<name>/beliefs/<agent>.ttl`](genesis/)); the wiring and the valve calibration are the
world's ([`world/`](world/)). Edit the files and restart the agent — no reflash.
The one thing firmware *does* enforce is the constitutional cadence clamp
(`MIN_SLEEP_S`/`MAX_SLEEP_S` in `config.h`) — a buggy agent must not be able to talk a board
into sleeping through a drought.

## Tests

The market layer (`clearing`, `auction`) is pure (no infra, no LLM), so it's fully unit-tested:

```bash
pip install -e ".[dev]"
pytest -q
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
the leash), wallet debiting + metabolic cost — which is also what makes *sensing* a priced
action, the one part of agent-driven sensing still missing — and the constitution as SHACL
over the trade.
See [`knowledge/decisions/roadmap.md`](knowledge/decisions/roadmap.md).
