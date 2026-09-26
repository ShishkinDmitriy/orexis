# Orexis

**ὄρεξις** — Aristotle's word for the desire that moves a creature to act. In *De Anima* III it
is the mover itself: reason alone moves nothing, and orexis is what turns a judgement into
motion. Its species there are *epithymia* (appetite), *thymos* (spirit) and **boulēsis**
(reasoned wish) — the last of which gives modal logic its word for desire, *bouletic*, which is
[what a want asserts here](knowledge/domain/modality.md).

The name points at the kernel rather than the shop floor: the market is one domain among several,
while the desiring mind is the part nothing swaps out. The project was called Agora and the rename says why —
[the-society-is-named-for-its-appetite](knowledge/decisions/the-society-is-named-for-its-appetite.md).

A society of self-interested agents that bid for a scarce resource, each one a BDI mind —
belief, desire, intention — deciding for itself under a hard trust boundary, grounded in real
sensors on a Raspberry Pi. **The domain is a plug-in**: plant watering is the example, not the
architecture. Architecture and rationale live in [`knowledge/`](knowledge/), an
[OKF](https://okf.md) bundle — start at
[`knowledge/decisions/index.md`](knowledge/decisions/index.md) §Start here.

**One process per agent.** Each is told only its own id and reads the rest from the documents
of the world it is given — what it acts for, which sensors are mounted there, which topics reach
them, what it wants — and each keeps its beliefs in a store of its own. A reading arrives, the
rules conclude which side of its subject's ranges it is on, a desire that reads unmet mints a
want, the search finds a plan of steps, and each step is taken by commanding a device or telling
a peer:

```
  board publishes            -> sensors/<probe>/reading     {"value": 0.18}
  agent believes, concludes  -> the reading, and that it is below its plot's range
  agent calls for water      -> agents/<host>/inbox         a call, as a document
  host offers a round        -> agents/<bidder>/inbox       a round, as a document
  bidder tenders, host clears, holder presents, host serves
                             -> actuators/<valve>/command   {"dose_ml": 500}
```

Nothing above is a name in the code. Every topic, every device and every limit is read from the
world's documents, in MQTT4SSN's and SOSA's words; the one instance identifier a process gets is
its own agent id. See [`world-graph`](knowledge/decisions/world-graph.md).

## Layout

```
agent/         Agent 0.2.0 — the store and the runtime, and the packages beside them: belief
               (revision by SHACL rules), sensing (bytes to an observation), prediction (when
               a reading changes range), planning (desires, wants, the search), execution
               (intentions and how a step is taken), speech (a peer's document) and the MQTT
               transport. No vocabulary for hardware and no word of any domain
domains/       vocabularies several worlds share — climate, actuation, market, hanoi, courier,
               sim — each an ontology, its actions and its rules, and no code
world/         the worlds — one directory each: its documents, each agent's own beliefs, its
               tests and its compose file
simulation/    the process a world runs to play the systems it says no one built
onboarding/    the sovereign's tools: what turns a world into a running society
firmware/      the ESP32 edge — what a board is flashed with
infra/         how it runs: the series store, grafana, and the broker image a world builds
tests/         the gates that read the whole tree
knowledge/     OKF knowledge bundle (architecture decisions + domain model)
```

**A world is documents, and each says which graph it is.** A Turtle file is one graph, and
`<> a orexis:WorldGraph` in it says what; a world imports the domains it speaks with
`owl:imports`, and an agent's desires are its own file under `beliefs/`. Adding a way of acting
is a node in a domain's `actions.ttl` — a precondition, an effect and an implementation — and a
world that imports the domain has it. See [`domain/world`](knowledge/domain/world.md) and
[`domain/action`](knowledge/domain/action.md).

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

**There is no default world.** Every command takes one as a required argument and refuses rather
than guessing, because a fallback puts a misconfigured agent on the same topics as the real one.

[`world/`](world/) holds one directory per world, each complete on its own, and each a directory
of documents that say which graph they are: `hanoi` and `courier`, puzzles an agent
solves and then stops; `greenhouse`, a heated bed the grower keeps comfortable by dosing and
heating it, played by the simulator; and `terrace`, a planter bed outdoors watched through a
FireBeetle 2 ESP32-E running `firmware/outdoor-sentinel`, a real board; and `sensing`, a fern
on a windowsill watched through a governed ESP32 that takes a cadence; and `allotment`, two
growers buying water from a supplier on a market. `tower` waits for planning on two levels. [`domain/world`](knowledge/domain/world.md) says what a world is made of, and
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

## Bringing a real board up

Start with the **smallest world**. `world/sensing` has one subject, one board and one agent,
which holds no desire: it reads, records and predicts, and wants nothing of the readings.

```bash
orexis-firmware sensing                # that board's config.h, from the world it belongs to
orexis-onboard sensing                 # one agent, sensing only
cd world/sensing && podman compose up -d
mosquitto_sub -t 'sensors/#' -v -p 1884       # or just watch the wire
```

A scheduled board is asleep almost all the time, so silence usually means it is working —
wait one interval. The interval is retained and therefore reliable; `{"sense":true}` is
best-effort and lands only if the board happens to be awake.

## Real hardware

A real ESP32 speaks the same protocol as the simulator — an agent can't tell them apart, so you
can mix them freely. A sensor `mqtt4ssn:observesTopic` the topic it publishes on and a board
`mqtt4ssn:listensToTopic` the one it takes commands on, each named by the filter that matches it;
both are whatever `world/<name>/world.ttl` says they are, and nothing is derived from an id. How
often a sensor reports is its `ssn-system:Frequency`, and the agent asks again for a reading fallen
due.

The board holds no policy. Ranges, what an agent wants and what a litre is worth to it are the
world's documents; edit them and restart the agent — no reflash. The one thing firmware *does*
enforce is the constitutional cadence clamp (`MIN_SLEEP_S`/`MAX_SLEEP_S` in `config.h`) — a buggy
agent must not be able to talk a board into sleeping through a drought.

## Tests

**The gates, and all must pass before a change is done.**

```bash
pip install -e ".[dev]"
pytest -q                    # agent/ and world/ — each world's own tests among them
pytest -q tests              # the four files that read the whole tree
lint-imports                 # onboarding may import agent, never the reverse
```

A world is held to what it does by the tests beside it, in `world/<name>/tests/`.

A third thing, run deliberately and **not** part of the two:

```bash
pytest infra -q -n0          # -n0 is REQUIRED: these rewrite one acl.conf in place
```

`infra/tests/` is a contract with mosquitto and InfluxDB rather than with this code — that a
revoked grant stops delivery to an already-connected client, that a rotated credential is refused
at once, that one agent's token cannot reach another's bucket. None of that is guaranteed by MQTT
or computed by anything here, so it is worth re-proving whenever those two change.

## What's next

**The loop closes: sensor-in → water-out,** and across agents: a plot reads dry, its grower buys
a claim on the supplier's water in a round it called for, and the supplier's valve opens — every
step a document one agent says to another, no model in the path.

Direction lives in [`roadmap`](knowledge/decisions/roadmap.md); what is known to be wrong lives in
the issue tracker, and what was deliberately left open lives in each record's *seams* section.

## License

MIT, see [`LICENSE`](LICENSE). The knowledge bundle under `knowledge/`, the worlds and the firmware are
under the same terms as the code.
