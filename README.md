# Orexis

**ὄρεξις** — Aristotle's word for the desire that moves a creature to act. In *De Anima* III it
is the mover itself: reason alone moves nothing, and orexis is what turns a judgement into
motion. Its species there are *epithymia* (appetite), *thymos* (spirit) and **boulēsis**
(reasoned wish) — the last of which gives modal logic its word for desire, *bouletic*, which is
[what a want asserts here](knowledge/domain/modality.md).

The name points at the kernel rather than the shop floor: the market is one capability among
several and the architecture's own showpiece of a replaceable implementation, while the desiring
mind is the part nothing swaps out. The project was called Agora and the rename says why —
[the-society-is-named-for-its-appetite](knowledge/decisions/the-society-is-named-for-its-appetite.md).

A society of self-interested agents that bid for a scarce resource, each one a BDI mind —
belief, desire, intention — deciding for itself under a hard trust boundary, grounded in real
sensors on a Raspberry Pi. **The domain is a plug-in**: plant watering is the example, not the
architecture. Architecture and rationale live in [`knowledge/`](knowledge/), an
[OKF](https://okf.md) bundle — start at
[`knowledge/decisions/index.md`](knowledge/decisions/index.md) §Start here.

**One process per agent.** Each is told only its own id and reads the rest from the belief
base — what it is wired to, what it can therefore do, and what it privately wants:

```
  agent asks its board      -> mqtt:commandTopic   {"sense":true} | {"sleep_s":N} retained
  board answers             -> mqtt:readingTopic   {"value":0.183,...}
  agent records + announces -> :sensed + Influx, then mqtt:eventTopic {"band":"LOW"}
  host opens a round        -> market:offerTopic   quantity, reserve, deadline
  each bidder answers       -> market:bidTopic/<id>   a number only it can compute
  host clears, claims go -> market:claimTopic/<id> -> owner opens its own valve
```

Nothing above is a name in the code. Every channel, every device, every limit is read from
the graph; the one instance identifier a process gets is its own agent id.

Agents are configured by **belief, not by file**. `:world` holds the public wiring — and from
that wiring genesis *derives* what each agent can do, so a scheduled sensor gives its agent a
cadence to own and a push-mode one does not. `:picks/<agent>` holds what each privately
wants. See [`capability-packages`](knowledge/decisions/capability-packages.md) and
[`world-graph`](knowledge/decisions/world-graph.md).

Trusted-agent mode: there is no gateway — each plant asserts its own reading. See
[`knowledge/decisions/trusted-agent-mode.md`](knowledge/decisions/trusted-agent-mode.md).

Sensing is **agent-timed**: the board only senses and sleeps; the *agent* decides how often to
look, and bids only on a fresh reading. See
[`knowledge/domain/sensing.md`](knowledge/domain/sensing.md).

## Layout

```
packages/      EVERY package there is, one mechanic: packages/<family>/<name>/
  bus/  part/    protocols, and the physical things — dht11, esp32, the probe, device
  plant/         what this society is about: the domain, and a species
  sim/           what stands in for hardware nobody built, and the physics it computes
  tool/          vocabularies a generator reads, not the society
  capability/    what an agent can DO — sensing, market, actuation, review, reporting
  transport/     how a device is REACHED — mqtt. Deliberately not a capability
  codec/  scaling/   how bytes become a document, and a document a quantity
  reactive/  progression/  deliberation/
                 the KERNEL, as three layers: a queue and the one thread that drains it;
                 the store engine, the intention ledger, the scheduler and the timer; the
                 belief base, the desires and the search. Each imports only the layers
                 beneath it, and speaks upward only as an event
agent/         the CONTAINER that assembles them: genesis, runtime, inference, validate, the
               Module contract. A BDI engine and nothing else — it holds no vocabulary for
               hardware, no mailbox, and no word for any domain
onboarding/    the sovereign's tools: what turns a ratified world into a running society
tests/         the two gates, plus the layering the image depends on
world/         ratified worlds — one directory each: topology, beliefs, and its compose file
firmware/      ESP32 edge — moisture sensors and pump/valve
infra/         how it runs: the infra compose, grafana and mosquitto configs
knowledge/     OKF knowledge bundle (architecture decisions + domain model)
```

**A directory is a PACKAGE** — not a capability. The two are not the same axis, and saying it
the other way hid that: `packages/orexis-capability-market/` provides three capabilities, and
`packages/orexis-part-esp32/` provides none. What isolates a capability is `PROVIDES` and its term.
Inside a package the same names mean the same things every time:

```
packages/orexis-capability-sensing/
  ontology.ttl   the vocabulary — what its terms mean
  shapes.ttl     the rules — what an agent must believe to hold it
  rules.ru       the derivation — what wiring GIVES an agent it
  terms.py       the terms it implements, and the families it asks others for
  beliefs.py     its Blocks — the private parameters it reads
  module.py      the code, which reads only that vocabulary
  __init__.py    the manifest: PROVIDES = (SubscribingModule, ListeningModule)
```

Every one of them is optional, and an omission is a statement: `domains/climate/` has no code,
`packages/orexis-transport-mqtt/` has no `rules.ru` because a transport grants no capability, and
`domains/actuation/` has no `beliefs.py` because it decides nothing.

Nothing lists these — `assembly.loader` finds them by looking, one level down, and the
FAMILY is the second segment of the package's own NAME rather than a directory above it or
anything declared. So **adding a capability is adding a directory**: drop in
`packages/orexis-capability-forecast/`, and agents load its vocabulary, run its
derivation, and boot with it if the wiring qualifies them. No registry line, no
term constant, no edit to any existing file — and deleting the directory removes it just as
completely, because capabilities reach each other through T-Box terms and never through
Python imports. See
[`capability-packages`](knowledge/decisions/capability-packages.md).

## Prerequisites

- Docker + Compose, **or** Podman + `podman-compose` (both work — the compose file is
  plain Compose-spec, rootless-friendly)
- Python 3.10+
- `mosquitto-clients` on the host, for `mosquitto_sub`. **Not the mosquitto server** — every
  broker here is a container, one per world, and installing the server package breaks them
  (see below)

## 1. Infra

```bash
cp infra/.env.example infra/.env                      # where the series store is (no secret)
cp infra/admin.env.example infra/secrets/admin.env    # the admin token — fill it in
orexis-infra-certs                                    # the services' certs and whom they trust
cd infra && podman compose up -d                      # or: docker compose up -d
```

Brings up **InfluxDB (`:8086`) and Grafana (`:3000`), and nothing else.** No triplestore — each
agent holds its own belief base inside its own container. **No broker either:** a broker belongs
to a world, not to the installation, so each world runs its own on its own port and neither can
hear the other. Grafana is pre-wired to InfluxDB over a **read-only** token, requires a login,
and serves HTTPS with a certificate from the installation CA — so your browser will warn until
you trust `infra/secrets/ca.crt`.

**A world's broker is built here rather than pulled**, and **refuses anonymous clients**: every
agent and every board connects as itself, and may reach only the topics the world wires it to.
The password file and the ACL behind that are generated by `orexis-mqtt <world>` from that
world's own wiring, so it must run before that world's broker will start.

`infra/mosquitto/Containerfile` is Debian + the stock `mosquitto` package. It is built rather
than pulled so the version is pinned — an upgrade should be a decision, not a side effect of
rebuilding — and so `entrypoint.sh` can keep a root shell as PID 1, which is what lets
`orexis-mqtt` reload the ACL without dropping a single connected agent.

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

Install `mosquitto-clients` on the host for `mosquitto_sub`/`mosquitto_pub` — every broker
itself is a container:

```bash
sudo apt install -y mosquitto-clients
```

If a **host** mosquitto is running from an earlier setup, disable it:
`sudo systemctl disable --now mosquitto`.

## 2. App

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 3. Run the slice

One-time setup, in order:

```bash
orexis-keygen simulation    # that world's host + clearing signing keys, once
orexis-validate simulation  # build the world from its files and hold it to every shape
```

**There is no default world.** Every command takes one as a required argument and refuses rather
than guessing, because a fallback puts a misconfigured agent on the same topics as the real one.

[`world/`](world/) holds one directory per world, each complete on its own, and each a directory
of documents that say which graph they are. On Agent 0.2.0: `hanoi` and `courier`, puzzles an agent
solves and then stops; `greenhouse`, a heated bed the grower keeps comfortable by dosing and
heating it, played by the simulator; and `terrace`, a planter bed outdoors watched through a
FireBeetle 2 ESP32-E running `firmware/outdoor-sentinel`, a real board; and `sensing`, a fern
on a windowsill watched through a governed ESP32 that takes a cadence. `tower` is still 0.1.0's,
waiting for planning on two levels. [`domain/world`](knowledge/domain/world.md) says what a world is made of, and
[`domain/domain`](knowledge/domain/domain.md) where the vocabulary several worlds share lives.

**There is nothing to seed and no store to provision.** A world is Turtle; each agent builds its
own belief base from it at boot and keeps it in a volume of its own, which nothing else can
open. Privacy is structural rather than enforced — see
[`where-the-belief-base-lives`](knowledge/decisions/where-the-belief-base-lives.md).

Bring a world up from the world — its broker's credentials and ACL, its series buckets, its
dashboards and its compose file are all generated from it:

```bash
orexis-mqtt greenhouse          # a credential per principal and the ACL, from the MQTT4SSN wiring
orexis-influx greenhouse        # a bucket per agent, and a token that opens only it
orexis-dashboards greenhouse    # a panel per sensor on what each agent acts for
orexis-compose greenhouse       # the broker, the simulator and one container per agent
cd world/greenhouse && podman compose up -d
```

Each agent is `orexis-agent <world> <id>`: it boots the world's documents, listens to the sensors on
what it acts for, writes every reading and what its rules conclude of it, predicts what comes
next, and plans and acts where a desire it holds reads unmet. An agent that holds only wants stops
when every one is reached; one that holds a desire, or that a transport reaches, runs for good.

**One container per agent, and that is the point.** On one filesystem every agent could read
every other agent's beliefs. Now each agent's belief base is a store in its own volume, locked
by its owner and unopenable by anything else — including you. See
[`domain/world`](knowledge/domain/world.md) §Deployment.

Note what is *not* born this way: firmware. A board is hardware and is flashed by hand, from the
`config.h` `orexis-firmware` generates out of the world it belongs to.

For unattended operation see [`runbooks/run-a-world`](knowledge/runbooks/run-a-world.md)
§Unattended — there are no orexis services, only podman's own restart handling.

## Running without hardware

**A simulation is a world**, not a flag or a mode. `world/greenhouse` needs no board at all: the
simulator (`python -m simulation <world>`, one more service in its compose file) is a process of
the world that plays every system the world marks `sim:simulatedBy`, from the world's own words —
the topics from MQTT4SSN, how often a sensor reports, how the bed dries and what a dose or a
heating does to it. See [`domain/domain`](knowledge/domain/domain.md).

**The agent cannot tell.** The simulator publishes on the same topics, speaks the same protocol and
is reached through the same kind of credential, so the mark that says a thing is played
(`sim:simulatedBy`) sits on the SYSTEM and never on the agent. An agent that could tell would be a
second code path, and a second code path is what a simulation exists to avoid.

## 4. Inspect

- **Grafana** — https://localhost:3000, a folder per world, generated by `orexis-dashboards`
  from what that world's agents actually observe. It **requires a login** and serves HTTPS with
  the installation CA's certificate, so your browser will warn until you trust
  `infra/secrets/ca.crt`. Datasource and dashboards are provisioned from `infra/grafana/` —
  recreating Grafana restores them, and nothing lives only in the container.
- **The wire** — `mosquitto_sub -t '#' -v -p <that world's port>`, which is the one place a
  society is visible from outside without asking anybody.
- **An agent's own mind** — `orexis-ask`, the sovereign's single question to a RUNNING agent
  over its world's bus. There is no shared store to query and no endpoint to point a browser
  at: a belief base is a file in its owner's volume, and this is disclosure rather than access,
  read-only by construction.

  ```bash
  orexis-ask simulation fern beliefs \
    'SELECT ?p ?v WHERE { ?s <http://www.w3.org/ns/sosa/hasSimpleResult> ?v ;
                             <http://www.w3.org/ns/sosa/observedProperty> ?p }'
  ```

  The modality is required — `beliefs` or `desires` — as the world is, because there is no
  default for either. See
  [`the-sovereign-may-ask`](knowledge/decisions/the-sovereign-may-ask.md).

## Bringing a real board up

Seed the **smallest world**. `world/sensing` has one subject, one
board and one agent, plumbed into no market — so derivation gives that agent `sensing:Subscribing`
and nothing else. It reads, records, and stops. Nothing in that world declares it sensor-only;
there is simply no market for a market capability to come from.

```bash
orexis-firmware sensing                # that board's config.h, from the world it belongs to
orexis-onboard sensing                 # one agent, sensing only
cd world/sensing && podman compose up -d
mosquitto_sub -t 'sensors/#' -v -p 1884       # or just watch the wire
```

`sensing` and `simulation` model the same probe identically — same id, same channels — so moving
a board between them is a credential swap and a reflash and **nothing else**: it is not
re-modelled, re-identified or re-granted. The model changed, not the firmware.

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
(`world/<name>/beliefs/<agent>.ttl`); the wiring and the valve calibration are the
world's ([`world/`](world/)). Edit the files and restart the agent — no reflash.
The one thing firmware *does* enforce is the constitutional cadence clamp
(`MIN_SLEEP_S`/`MAX_SLEEP_S` in `config.h`) — a buggy agent must not be able to talk a board
into sleeping through a drought.

## Tests

**Two gates, and both must pass before a change is done.**

```bash
pip install -e ".[dev]"
pytest -q                    # agent/, packages/ and world/; the 0.1.0 suite in tests/ is switched off
orexis-validate simulation   # and every other world you have
lint-imports                 # the layering: onboarding may import agent, never the reverse
```

`orexis-validate` holds a world to every package's `shapes.ttl`, and the checks are
**capability-aware**: a rule applies to an agent only if the world derived that capability for
it. So the supplier is never asked for a cadence, a subscribing agent must have one, and a
listening agent must *not* — plus the usual: a band whose floor is below its ceiling, a cadence
that watches more closely when thirsty, nobody sleeping past the constitutional ceiling, and
every device stating where it is reachable.

A third thing, run deliberately and **not** part of the two:

```bash
pytest infra -q -n0          # -n0 is REQUIRED: these rewrite one acl.conf in place
```

`infra/tests/` is a contract with mosquitto and InfluxDB rather than with this code — that a
revoked grant stops delivery to an already-connected client, that a rotated credential is refused
at once, that one agent's token cannot reach another's bucket. None of that is guaranteed by MQTT
or computed by anything here, so it is worth re-proving whenever those two change.

## What's next

**The loop closes: sensor-in → water-out.** A plant reads its own soil, decides for itself that
it is short, bids a number nobody else can compute, and the winner's valve opens — deterministic,
no model in the path.

Built since that sentence was first written, and worth knowing before you read the code: a
**desire is a SHACL shape** and its force is a severity, so pursuing is validating; an
**intention is the head of a plan committed to**, re-derived every pass because the world moves;
**deliberation searches possible worlds** as graph diffs; an agent given room to move
**re-picks its own settings** on its own clock; a **round is a fact** on both sides, so buying
has a real precondition; and the market is one package among several, replaceable, reached only
through T-Box terms.

Next: the **LLM stance** layer — justification and coalition on top of the deterministic number,
on a leash — wallet debiting and metabolic cost, which is also what makes *sensing* a priced
action, and the constitution as SHACL over the trade. Direction lives in
[`roadmap`](knowledge/decisions/roadmap.md); what is known to be wrong lives in the issue
tracker, and what was deliberately left open lives in each record's *seams* section.

## License

MIT, see [`LICENSE`](LICENSE). The knowledge bundle under `knowledge/`, the worlds and the firmware are
under the same terms as the code.
